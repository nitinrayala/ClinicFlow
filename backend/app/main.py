import logging
import time
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import delete, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from . import ai
from .auth import COOKIE_NAME, DUMMY_HASH, create_session, current_user, doctor, password_hasher, rate_limit, token_hash
from .config import get_settings
from .db import get_db
from .models import Appointment, AuthSession, AuditEvent, Encounter, Generation, Patient, Task, TranscriptVersion, User, utcnow
from .schemas import LoginRequest, RevisionRequest, SaveEncounter, TaskUpdate
from .services import audit, check_revision, encounter_json, generation_json, generation_matches, get_encounter, patient_age, review_required, reviewed_note, snapshot, task_json, user_json, validate_assignee

settings = get_settings()
logger = logging.getLogger("clinicflow")
app = FastAPI(title="ClinicFlow", version="1.0.0", description="Fictional dermatology documentation demo. Human approval required.")
app.add_middleware(CORSMiddleware, allow_origins=settings.origins, allow_credentials=True,
                   allow_methods=["GET", "POST", "PUT", "PATCH"], allow_headers=["Content-Type"])


@app.middleware("http")
async def request_guards(request: Request, call_next):
    if request.url.path.startswith("/api") and request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        origin = request.headers.get("origin")
        referer = request.headers.get("referer")
        if not origin and referer:
            parts = urlsplit(referer)
            origin = f"{parts.scheme}://{parts.netloc}"
        if origin and origin.rstrip("/") not in settings.origins:
            return JSONResponse({"detail": "Request origin is not allowed."}, status_code=403)
        if request.headers.get("sec-fetch-site") == "cross-site" and not origin:
            return JSONResponse({"detail": "Cross-site request rejected."}, status_code=403)
        size = request.headers.get("content-length", "0")
        if not size.isdigit() or int(size) > 256000:
            return JSONResponse({"detail": "Request is too large."}, status_code=413)
        if int(size) > 0 and request.headers.get("content-type", "").split(";")[0] != "application/json":
            return JSONResponse({"detail": "Send an application/json request."}, status_code=415)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Cache-Control"] = "no-store" if request.url.path.startswith("/api") else "no-cache"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    if settings.cookie_secure:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


@app.exception_handler(RequestValidationError)
async def invalid_request(request: Request, error: RequestValidationError):
    # Pydantic errors can include input/transcripts; return only field names and generic descriptions.
    fields = ", ".join(".".join(str(p) for p in item["loc"][1:]) for item in error.errors()[:5])
    return JSONResponse({"detail": f"Invalid request fields: {fields}. Check required fields and input limits."}, status_code=422)


@app.exception_handler(SQLAlchemyError)
async def database_failure(request: Request, error: SQLAlchemyError):
    logger.error("database_request_failed error_type=%s", type(error).__name__)
    return JSONResponse({"detail": "The database request could not be completed. Your changes were not saved; please retry."}, status_code=503)


@app.get("/api/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "ok", "ai_mode": settings.ai_mode}


@app.post("/api/auth/login")
def login(body: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    ip = request.client.host if request.client else "unknown"
    rate_limit(db, "login", f"{email}:{ip}", settings.login_limit_per_minute, 60)
    user = db.scalar(select(User).where(User.email == email))
    valid = password_hasher.verify(body.password, user.password_hash if user else DUMMY_HASH)
    if not user or not valid:
        raise HTTPException(401, "Email or password is incorrect.")
    previous = request.cookies.get(COOKIE_NAME)
    if previous:
        db.execute(delete(AuthSession).where(AuthSession.token_hash == token_hash(previous)))
    token = create_session(db, user)
    db.commit()
    response.set_cookie(COOKIE_NAME, token, httponly=True, secure=settings.cookie_secure, samesite="lax",
                         max_age=settings.session_hours * 3600, path="/api")
    return user_json(db, user)


@app.get("/api/auth/me")
def me(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return user_json(db, user)


@app.post("/api/auth/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    token = request.cookies.get(COOKIE_NAME)
    if token:
        db.execute(delete(AuthSession).where(AuthSession.token_hash == token_hash(token)))
        db.commit()
    response.delete_cookie(COOKIE_NAME, path="/api", secure=settings.cookie_secure, httponly=True, samesite="lax")
    return {"ok": True}


@app.get("/api/team")
def team(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return [user_json(db, member) for member in db.scalars(select(User).where(User.clinic_id == user.clinic_id).order_by(User.name))]


@app.get("/api/appointments")
def appointments(user: User = Depends(doctor), db: Session = Depends(get_db)):
    rows = db.execute(select(Appointment, Patient, Encounter).join(Patient, Appointment.patient_id == Patient.id)
        .outerjoin(Encounter, Encounter.appointment_id == Appointment.id)
        .where(Appointment.clinic_id == user.clinic_id).order_by(Appointment.scheduled_at)).all()
    return [{"id": a.id, "patient_id": p.id, "patient_name": p.name,
             "patient_age": patient_age(p, a.scheduled_at.date()), "patient_initials": "".join(part[0] for part in p.name.split()[:2]),
             "scheduled_at": a.scheduled_at, "reason": a.reason, "status": e.status if e else "scheduled", "encounter_id": e.id if e else None}
            for a, p, e in rows]


@app.post("/api/appointments/{appointment_id}/encounter")
def open_encounter(appointment_id: str, user: User = Depends(doctor), db: Session = Depends(get_db)):
    appointment = db.scalar(select(Appointment).where(Appointment.id == appointment_id, Appointment.clinic_id == user.clinic_id).with_for_update())
    if appointment is None:
        raise HTTPException(404, "Appointment not found.")
    encounter = db.scalar(select(Encounter).where(Encounter.appointment_id == appointment.id))
    if encounter is None:
        encounter = Encounter(appointment_id=appointment.id, clinic_id=user.clinic_id)
        db.add(encounter)
        db.flush()
        db.add(TranscriptVersion(encounter_id=encounter.id, clinic_id=user.clinic_id, revision=0, text=""))
        snapshot(db, encounter, user, "created")
        audit(db, encounter, user, "encounter_opened")
    db.commit()
    return encounter_json(db, encounter)


@app.get("/api/encounters/{encounter_id}")
def encounter_detail(encounter_id: str, user: User = Depends(doctor), db: Session = Depends(get_db)):
    encounter = get_encounter(db, encounter_id, user)
    # Synchronous requests are bounded. Recover abandoned status after a crashed worker without retrying a paid request.
    if encounter.generation_status == "running" and encounter.current_generation_id:
        generation = db.get(Generation, encounter.current_generation_id)
        if generation and generation.created_at < utcnow() - timedelta(seconds=settings.provider_timeout_seconds + 30):
            encounter = get_encounter(db, encounter_id, user, lock=True)
            if encounter.current_generation_id == generation.id and encounter.generation_status == "running":
                generation.status = "failed"
                encounter.generation_status = "failed"
                db.commit()
    return encounter_json(db, encounter)


@app.put("/api/encounters/{encounter_id}")
def save_encounter(encounter_id: str, body: SaveEncounter, user: User = Depends(doctor), db: Session = Depends(get_db)):
    encounter = get_encounter(db, encounter_id, user, lock=True)
    check_revision(encounter, body)
    for proposal in body.proposed_tasks:
        validate_assignee(db, proposal.assignee_id, user)
    transcript_changed = body.transcript != encounter.transcript
    note = reviewed_note(encounter, body, transcript_changed)
    tasks = [task.model_dump(mode="json") for task in body.proposed_tasks]
    old_tasks = {task["id"]: task for task in encounter.proposed_tasks}
    for task in tasks:
        task["evidence"] = old_tasks.get(task["id"], {}).get("evidence", [])
    draft_changed = note != encounter.note or tasks != encounter.proposed_tasks
    if transcript_changed:
        encounter.transcript_revision += 1
        encounter.transcript = body.transcript
        db.add(TranscriptVersion(clinic_id=user.clinic_id, encounter_id=encounter.id,
                                  revision=encounter.transcript_revision, text=body.transcript))
    if draft_changed:
        encounter.draft_revision += 1
        encounter.note, encounter.proposed_tasks = note, tasks
    if transcript_changed or draft_changed:
        if encounter.generation_status in {"running", "succeeded"}:
            encounter.generation_status = "stale"
        snapshot(db, encounter, user, "saved")
        audit(db, encounter, user, "draft_saved", draft_revision=encounter.draft_revision, transcript_revision=encounter.transcript_revision)
    db.commit()
    return encounter_json(db, encounter)


@app.post("/api/encounters/{encounter_id}/generate")
def generate(encounter_id: str, body: RevisionRequest, user: User = Depends(doctor), db: Session = Depends(get_db)):
    # Check ownership before charging a user's rate budget.
    get_encounter(db, encounter_id, user)
    rate_limit(db, "generate", user.id, settings.generation_limit_per_hour, 3600)
    encounter = get_encounter(db, encounter_id, user, lock=True)
    check_revision(encounter, body)
    if not encounter.transcript.strip():
        raise HTTPException(422, "Save a transcript before generating a draft.")
    generation = Generation(encounter_id=encounter.id, clinic_id=user.clinic_id,
        draft_revision=encounter.draft_revision, transcript_revision=encounter.transcript_revision,
        provider=settings.ai_mode, prompt_version=ai.PROMPT_VERSION)
    db.add(generation)
    db.flush()
    encounter.current_generation_id = generation.id
    encounter.generation_status = "running"
    transcript = encounter.transcript
    audit(db, encounter, user, "generation_started", generation_id=generation.id)
    db.commit()  # Release row lock while the provider is working. Draft editing remains available.
    started = time.perf_counter()
    try:
        output, provider = ai.extract(transcript)
        note, proposals = ai.materialize(output, transcript, generation.transcript_revision, generation.id)
    except ai.ProviderFailure as error:
        encounter = get_encounter(db, encounter_id, user, lock=True)
        generation.status = "failed"
        generation.latency_ms = int((time.perf_counter() - started) * 1000)
        if encounter.current_generation_id == generation.id:
            encounter.generation_status = "failed"
        audit(db, encounter, user, "generation_failed", generation_id=generation.id)
        db.commit()
        logger.warning("generation_failed generation_id=%s status=%s", generation.id, error.status_code)
        raise HTTPException(error.status_code, str(error)) from error
    encounter = get_encounter(db, encounter_id, user, lock=True)
    generation.note, generation.proposed_tasks, generation.provider = note, proposals, provider
    generation.latency_ms = int((time.perf_counter() - started) * 1000)
    if not generation_matches(encounter, generation):
        generation.status = "stale"
        if encounter.current_generation_id == generation.id:
            encounter.generation_status = "stale"
        audit(db, encounter, user, "generation_stale", generation_id=generation.id)
        db.commit()
        raise HTTPException(409, "This generation is stale because the visit changed or a newer generation started. Your saved work is unchanged.")
    generation.status = encounter.generation_status = "succeeded"
    audit(db, encounter, user, "generation_ready", generation_id=generation.id)
    db.commit()
    return generation_json(generation)


@app.post("/api/encounters/{encounter_id}/generations/{generation_id}/apply")
def apply_generation(encounter_id: str, generation_id: str, body: RevisionRequest, user: User = Depends(doctor), db: Session = Depends(get_db)):
    encounter = get_encounter(db, encounter_id, user, lock=True)
    check_revision(encounter, body)
    generation = db.scalar(select(Generation).where(Generation.id == generation_id,
        Generation.encounter_id == encounter.id, Generation.clinic_id == user.clinic_id))
    if generation is None:
        raise HTTPException(404, "Generation not found.")
    if generation.status != "succeeded" or not generation_matches(encounter, generation):
        raise HTTPException(409, "This candidate can no longer replace the saved draft. Generate a new candidate.")
    snapshot(db, encounter, user, "before_generation")
    encounter.note, encounter.proposed_tasks = generation.note, generation.proposed_tasks
    encounter.draft_revision += 1
    generation.status = "applied"
    snapshot(db, encounter, user, "generation_applied")
    audit(db, encounter, user, "generation_applied", generation_id=generation.id, draft_revision=encounter.draft_revision)
    db.commit()
    return encounter_json(db, encounter)


@app.post("/api/encounters/{encounter_id}/approve")
def approve(encounter_id: str, body: RevisionRequest, user: User = Depends(doctor), db: Session = Depends(get_db)):
    encounter = get_encounter(db, encounter_id, user, lock=True)
    if encounter.status == "approved" and (body.draft_revision, body.transcript_revision) == (
        encounter.approved_draft_revision, encounter.approved_transcript_revision):
        return encounter_json(db, encounter)
    check_revision(encounter, body)
    if not any(encounter.note.values()):
        raise HTTPException(422, "Add at least one documented note fact before approving.")
    if review_required(encounter):
        raise HTTPException(422, "Acknowledge the historical evidence for each edited or source-changed fact before approving.")
    for proposal in encounter.proposed_tasks:
        validate_assignee(db, proposal["assignee_id"], user)
        db.add(Task(clinic_id=user.clinic_id, encounter_id=encounter.id, proposal_id=proposal["id"],
            description=proposal["description"], due_date=date.fromisoformat(proposal["due_date"]) if proposal["due_date"] else None,
            assignee_id=proposal["assignee_id"]))
    encounter.status = "approved"
    encounter.approved_at, encounter.approved_by = utcnow(), user.id
    encounter.approved_draft_revision, encounter.approved_transcript_revision = body.draft_revision, body.transcript_revision
    if encounter.generation_status == "running":
        encounter.generation_status = "stale"
    snapshot(db, encounter, user, "approved")
    audit(db, encounter, user, "note_approved", draft_revision=body.draft_revision, task_count=len(encounter.proposed_tasks))
    db.commit()  # Approved snapshot, tasks and audit either all commit, or all roll back.
    return encounter_json(db, encounter)


@app.get("/api/encounters/{encounter_id}/audit")
def encounter_audit(encounter_id: str, user: User = Depends(doctor), db: Session = Depends(get_db)):
    get_encounter(db, encounter_id, user)
    return [{"id": event.id, "action": event.action, "actor_name": actor.name, "created_at": event.created_at, "details": event.details}
        for event, actor in db.execute(select(AuditEvent, User).join(User, AuditEvent.actor_id == User.id)
        .where(AuditEvent.encounter_id == encounter_id, AuditEvent.clinic_id == user.clinic_id).order_by(AuditEvent.created_at))]


@app.get("/api/tasks")
def tasks(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return [task_json(db, task) for task in db.scalars(select(Task).where(Task.clinic_id == user.clinic_id).order_by(Task.created_at.desc()))]


def locked_task(db: Session, task_id: str, user: User) -> Task:
    task = db.scalar(select(Task).where(Task.id == task_id, Task.clinic_id == user.clinic_id).with_for_update().execution_options(populate_existing=True))
    if task is None:
        raise HTTPException(404, "Task not found.")
    return task


@app.post("/api/tasks/{task_id}/claim")
def claim_task(task_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    task = locked_task(db, task_id, user)
    if task.assignee_id is not None and task.assignee_id != user.id:
        raise HTTPException(409, "Another clinic member already claimed this task.")
    if task.assignee_id is None:
        task.assignee_id = user.id
        audit(db, db.get(Encounter, task.encounter_id), user, "task_claimed", task_id=task.id)
    db.commit()
    return task_json(db, task)


@app.patch("/api/tasks/{task_id}")
def update_task(task_id: str, body: TaskUpdate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    task = locked_task(db, task_id, user)
    if user.role != "doctor" and (task.assignee_id != user.id or "assignee_id" in body.model_fields_set):
        raise HTTPException(403, "Staff can update only their own tasks. Claim an unassigned task first.")
    if "assignee_id" in body.model_fields_set:
        validate_assignee(db, body.assignee_id, user)
        task.assignee_id = body.assignee_id
    if body.status is not None:
        task.status = body.status
    audit(db, db.get(Encounter, task.encounter_id), user, "task_updated", task_id=task.id, status=task.status, assignee_id=task.assignee_id)
    db.commit()
    return task_json(db, task)


# One-origin production bundle. API routes must remain registered before the SPA fallback.
static_dir = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if static_dir.is_dir():
    assets = static_dir / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        if path == "api" or path.startswith("api/"):
            raise HTTPException(404, "API endpoint not found.")
        requested = (static_dir / path).resolve()
        if requested.is_relative_to(static_dir) and requested.is_file():
            return FileResponse(requested)
        return FileResponse(static_dir / "index.html")
