# ClinicFlow implementation contract

All endpoints below are prefixed `/api`. JSON uses snake_case. IDs are strings (UUIDs). Dates are ISO strings. Error shape is `{detail: string}`. Auth uses an HttpOnly same-site session cookie; Vite proxies `/api` in development. Mutations require same-origin validation. Doctor/staff roles come from the authenticated server session.

## Endpoints

- `GET /health` -> `{status: "ok", database: "ok", ai_mode: "demo" | "live" | "disabled"}`.
- `POST /auth/login` `{email,password}` -> User, sets session cookie.
- `GET /auth/me` -> User; `POST /auth/logout` -> `{ok:true}`.
- User: `{id,name,email,role,clinic_id,clinic_name}`.
- `GET /appointments` -> Appointment[]. `{id,patient_id,patient_name,patient_age,patient_initials,scheduled_at,reason,status,encounter_id}`. Doctor only.
- `POST /appointments/{id}/encounter` -> Encounter (existing or new). Doctor only.
- `GET /encounters/{id}` -> Encounter. Doctor only.
- `PUT /encounters/{id}` `{draft_revision,transcript_revision,transcript,note,proposed_tasks}` -> Encounter; 409 on stale/approved.
- `POST /encounters/{id}/generate` `{draft_revision,transcript_revision}` -> Generation. Does not replace draft; returns candidate. 409 for changed/approved/superseded during request. Missing live key -> actionable 503; demo mode explicitly labeled.
- `POST /encounters/{id}/generations/{generation_id}/apply` `{draft_revision,transcript_revision}` -> Encounter. Guard captured revisions/current request/state; preserve history.
- `POST /encounters/{id}/approve` `{draft_revision,transcript_revision}` -> Encounter (idempotent for originally approved revision).
- `GET /encounters/{id}/audit` -> `{id,action,actor_name,created_at,details}`[].
- `GET /team` -> User[] in current clinic.
- `GET /tasks` -> Task[] for clinic (staff and doctors); frontend groups mine/unassigned/all, backend permits assigned-task mutations only to assigned user or doctor.
- `POST /tasks/{id}/claim` -> Task (atomic, 409 if owned by another).
- `PATCH /tasks/{id}` `{status?,assignee_id?}` -> Task (doctor can assign only same-clinic users; staff updates own tasks).

## Data shapes

Encounter: `{id,appointment_id,patient_name,patient_age,reason,scheduled_at,status,transcript,transcript_revision,draft_revision,note,proposed_tasks,generation_status,approved_at,approved_by}`.

Note: `{symptoms: Fact[],history: Fact[],findings: Fact[],plan: Fact[]}`. Empty sections display `Not documented`.

Fact: `{id,text,origin:"manual"|"ai"|"doctor-edited",evidence: Evidence[],evidence_reviewed:boolean}`.

Evidence: `{segment_id,quote,transcript_revision}`. Segment IDs are `s1`, `s2`, etc for nonempty transcript lines (not sentence splitting). UI can highlight these exact lines. Evidence returned with encounter may include original `source_text` for immutable source display; server must maintain original transcript revision snapshots.

ProposedTask: `{id,description,due_date:string|null,assignee_id:string|null,evidence:Evidence[],timing_text?:string|null}`.

Generation: `{id,note,proposed_tasks,transcript_revision,draft_revision,provider,created_at}`.

Task: `{id,encounter_id,patient_name,description,due_date,assignee_id,assignee_name,status,created_at}`.

## Demo seed

Demo mode must be explicit (`AI_MODE=demo`), with a visible banner distinguishing deterministic examples from live AI. No network calls in automated tests. Seed uses `DEMO_PASSWORD` environment variable, local documented example only. Accounts: `doctor@clinicflow.demo`, `staff@clinicflow.demo`, `doctor@other.demo`, `staff@other.demo`. Two fictional clinics. First clinic name: Willow Dermatology; doctor name Dr. Maya Chen; staff Jamie Rivera. At least six appointments with meaningful fictional transcripts. The first is Avery Morgan, rash review.

Runtime module `app.main:app`, configuration `DATABASE_URL`, `AI_MODE`, `OPENAI_API_KEY` (empty), `OPENAI_MODEL` (empty), `DEMO_PASSWORD` (empty example), `ALLOWED_ORIGINS`, `COOKIE_SECURE`, `APP_ENV`. Auth sessions are random tokens hashed in DB with expiration and logout revocation, passwords Argon2 via pwdlib. Tables migrated by Alembic. All local/demo identity shortcuts forbidden in production endpoints.
