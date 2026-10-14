from copy import deepcopy
from datetime import date

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Appointment, AuditEvent, Clinic, Encounter, Generation, NoteVersion, Patient, Task, User
from .schemas import RevisionRequest, SaveEncounter


def user_json(db: Session, user: User) -> dict:
    clinic = db.get(Clinic, user.clinic_id)
    return {"id": user.id, "name": user.name, "email": user.email, "role": user.role,
            "clinic_id": user.clinic_id, "clinic_name": clinic.name}


def patient_age(patient: Patient, on_date: date) -> int:
    dob = patient.date_of_birth
    return on_date.year - dob.year - ((on_date.month, on_date.day) < (dob.month, dob.day))


def encounter_json(db: Session, encounter: Encounter) -> dict:
    appointment = db.get(Appointment, encounter.appointment_id)
    patient = db.get(Patient, appointment.patient_id)
    actor = db.get(User, encounter.approved_by) if encounter.approved_by else None
    return {"id": encounter.id, "appointment_id": encounter.appointment_id, "patient_name": patient.name,
            "patient_age": patient_age(patient, appointment.scheduled_at.date()), "reason": appointment.reason,
            "scheduled_at": appointment.scheduled_at, "status": encounter.status,
            "transcript": encounter.transcript, "transcript_revision": encounter.transcript_revision,
            "draft_revision": encounter.draft_revision, "note": encounter.note, "proposed_tasks": encounter.proposed_tasks,
            "generation_status": encounter.generation_status, "approved_at": encounter.approved_at,
            "approved_by": actor.name if actor else None}


def task_json(db: Session, task: Task) -> dict:
    encounter = db.get(Encounter, task.encounter_id)
    appointment = db.get(Appointment, encounter.appointment_id)
    patient = db.get(Patient, appointment.patient_id)
    assignee = db.get(User, task.assignee_id) if task.assignee_id else None
    return {"id": task.id, "encounter_id": task.encounter_id, "patient_name": patient.name,
            "description": task.description, "due_date": task.due_date, "assignee_id": task.assignee_id,
            "assignee_name": assignee.name if assignee else None, "status": task.status, "created_at": task.created_at}


def generation_json(generation: Generation) -> dict:
    return {"id": generation.id, "note": generation.note, "proposed_tasks": generation.proposed_tasks,
            "transcript_revision": generation.transcript_revision, "draft_revision": generation.draft_revision,
            "provider": generation.provider, "created_at": generation.created_at}


def get_encounter(db: Session, encounter_id: str, user: User, lock: bool = False) -> Encounter:
    query = select(Encounter).where(Encounter.id == encounter_id, Encounter.clinic_id == user.clinic_id)
    if lock:
        query = query.with_for_update().execution_options(populate_existing=True)
    encounter = db.scalar(query)
    if encounter is None:
        raise HTTPException(404, "Encounter not found.")
    return encounter


def check_revision(encounter: Encounter, request: RevisionRequest):
    if encounter.status != "draft":
        raise HTTPException(409, "This note is approved and can no longer be edited.")
    if (encounter.draft_revision, encounter.transcript_revision) != (request.draft_revision, request.transcript_revision):
        raise HTTPException(409, "The visit changed since you opened it. Reload the saved version before continuing.")


def validate_assignee(db: Session, assignee_id: str | None, user: User):
    if assignee_id is not None and db.scalar(select(User.id).where(User.id == assignee_id, User.clinic_id == user.clinic_id)) is None:
        raise HTTPException(422, "Task assignees must belong to your clinic.")


def snapshot(db: Session, encounter: Encounter, user: User, kind: str):
    db.add(NoteVersion(clinic_id=encounter.clinic_id, encounter_id=encounter.id,
        draft_revision=encounter.draft_revision, transcript_revision=encounter.transcript_revision,
        note=deepcopy(encounter.note), proposed_tasks=deepcopy(encounter.proposed_tasks), kind=kind, actor_id=user.id))


def audit(db: Session, encounter: Encounter, user: User, action: str, **details):
    # Details contain identifiers/revisions only; never transcript or generated content.
    db.add(AuditEvent(clinic_id=encounter.clinic_id, encounter_id=encounter.id,
                      actor_id=user.id, action=action, details=details))


def reviewed_note(encounter: Encounter, request: SaveEncounter, transcript_changed: bool) -> dict:
    """Keep server-owned provenance. Changing a claim requires a separate acknowledgement save."""
    incoming = request.note.model_dump(mode="json")
    previous = {fact["id"]: (section, fact) for section, facts in encounter.note.items() for fact in facts}
    for section, facts in incoming.items():
        for fact in facts:
            old_entry = previous.get(fact["id"])
            if old_entry is None:
                fact.update(origin="manual", evidence=[], evidence_reviewed=False)
                continue
            old_section, old = old_entry
            fact["evidence"] = deepcopy(old["evidence"])
            changed = fact["text"] != old["text"] or old_section != section
            fact["origin"] = "doctor-edited" if changed and old["origin"] in {"ai", "doctor-edited"} else old["origin"]
            if (changed or transcript_changed) and fact["evidence"]:
                fact["evidence_reviewed"] = False
            elif not fact["evidence"]:
                fact["evidence_reviewed"] = False
    return incoming


def review_required(encounter: Encounter) -> bool:
    return any(fact["evidence"] and not fact["evidence_reviewed"] and (
        fact["origin"] == "doctor-edited" or any(ref["transcript_revision"] != encounter.transcript_revision for ref in fact["evidence"]))
        for facts in encounter.note.values() for fact in facts)


def generation_matches(encounter: Encounter, generation: Generation) -> bool:
    return (encounter.status == "draft" and encounter.current_generation_id == generation.id
            and encounter.transcript_revision == generation.transcript_revision
            and encounter.draft_revision == generation.draft_revision)
