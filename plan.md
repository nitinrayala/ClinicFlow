# ClinicFlow build plan

## Goal

Build a job portfolio application that takes a fictional patient visit from a consultation transcript to a reviewed note and assigned follow-up tasks.

The finished demo should show one complete workflow:

**Open appointment -> enter transcript -> generate draft -> review evidence and edit -> approve note -> complete follow-up tasks.**

This project targets the ModMed Software Engineer 1, Trainee role. It should demonstrate Python development, a usable React interface, SQL, AI integration, cloud deployment, and reliable application behavior. The JD does not establish a mandatory language or database.

## Stack and boundaries

| Area | Choice |
| --- | --- |
| Backend | Python, FastAPI, Pydantic |
| Database | PostgreSQL, SQLAlchemy, Alembic migrations |
| Frontend | React, TypeScript, Vite, React Router |
| Styling | Start with plain CSS and a small set of reusable components |
| AI | One provider's official Python SDK, called from the backend |
| Tests | pytest for backend behavior; Playwright for the main browser workflow |
| Local environment | Python virtual environment; Docker Compose for PostgreSQL |
| Delivery | Docker, GitHub Actions, one cloud provider selected in Phase 1 |

- Use fictional patients and transcripts throughout the demo.
- Start with text input and one specialty: dermatology.
- Extract documented facts and the clinician's stated plan. Do not generate diagnoses or treatment recommendations.
- Missing information stays `not documented`.
- Follow-up tasks become actionable only after a doctor approves the note.
- Build a modular application with one backend and one database. Add infrastructure only when a working feature needs it.
- Complete each phase's finish line before moving on. Each checkbox is intended to be a small task or commit; split it further if it feels too large.

## Milestones

| Milestone | Phases | Demonstrable result |
| --- | --- | --- |
| 1. Manual clinic application | 1-5 | Appointments, editable notes, login, approval, and visible staff tasks; a basic hosted version is running after Phase 3. |
| 2. AI-assisted workflow | 6 | Structured generation, evidence links, doctor review, and failure handling without overwriting edits. |
| 3. Portfolio-ready demo | 7-8 | Measured evaluation results, deployment polish, documentation, and a walkthrough. |

The checklist guides implementation; it is not a requirement to master every tool before progressing. This is a substantial portfolio project, so finish one small behavior at a time.

## Phase 1: Get a small application running

**Outcome:** the browser can reach the Python backend and the backend can reach PostgreSQL.

- [ ] Create `backend/`, `frontend/`, `docs/`, and `tests/` where appropriate.
- [ ] Set up FastAPI with a health endpoint and environment-based configuration.
- [ ] Start PostgreSQL through Docker Compose and connect using SQLAlchemy.
- [ ] Initialize Alembic and create the first migration.
- [ ] Create the React + TypeScript app with Vite and show the backend health status.
- [ ] Add `.env.example`, ignore secrets and generated files, and document local startup commands.
- [ ] Choose one hosting target after checking current pricing and support for the frontend, Python backend, and managed PostgreSQL. Record the choice and configure a budget alert where supported.

**Finish line:** a fresh checkout can start both apps and the database using the README instructions. The page shows a successful backend connection.

**Learn as needed:** HTTP requests, JSON, environment variables, JavaScript promises, and `async/await`.

## Phase 2: Model visits and save manual notes

**Outcome:** a visit can be opened, edited, saved, and reopened without AI.

- [ ] Add tables for clinics, users, patients, appointments, encounters, and note versions.
- [ ] Give clinic-owned records a clinic ID and define foreign keys and required fields.
- [ ] Add a repeatable seed command with two fictional clinics, doctor/staff users, patients, and appointments.
- [ ] Build APIs to list appointments, open an encounter, and save its transcript and draft note.
- [ ] Store structured note sections: symptoms, relevant history, findings, and stated plan.
- [ ] Add a version number to editable encounters so stale saves can be rejected rather than overwrite newer edits.
- [ ] Document encounter states and transitions: `draft` is editable and `approved` is immutable. Track generation separately as `idle`, `running`, `succeeded`, `failed`, or `stale` so a running request does not lock the doctor's editing workflow.
- [ ] Define independent transcript revisions and draft revisions. Every saved change increments the relevant revision; approval verifies the current draft revision and changes the encounter state atomically.
- [ ] Define generation acceptance rules now: capture transcript revision, draft revision, and request ID at start. Apply a result only while both revisions match, the encounter is still a draft, and the request is still current. Recheck atomically when applying the result.
- [ ] Test saving, reopening, invalid input, and stale updates against a test PostgreSQL database.
- [ ] Start GitHub Actions CI with backend tests against PostgreSQL and migration setup; run it on pull requests and pushes.

**Finish line:** using the API documentation, open an appointment, save a manual note, and retrieve it after restarting the backend.

**Scope note:** temporary development identity is acceptable locally in this phase. Replace it in Phase 4 before sharing the app.

## Phase 3: Build the first usable screens

**Outcome:** the manual visit workflow works in the browser.

- [ ] Create the appointments screen with fictional patient names, visit times, and statuses.
- [ ] Create the encounter workspace with transcript input and editable note sections.
- [ ] Connect the screens to the backend through a small typed API client.
- [ ] Add loading, empty, error, saving, and saved states.
- [ ] Preserve unsaved text after a failed request and warn before navigating away with unsaved changes.
- [ ] Use labeled inputs, visible keyboard focus, readable contrast, and a layout that works on laptop and narrow screens.
- [ ] Add frontend type checks and a production build to the existing CI workflow.
- [ ] Prepare a backend container and deploy a basic frontend, backend, and PostgreSQL instance to the chosen host. Verify migrations, environment variables, HTTPS, CORS, and database connectivity.
- [ ] Keep this early deployment behind host-level access protection until Phase 4 replaces development identity with application login and permissions.

**Finish line:** select an appointment, enter a transcript, edit a manual note, save it, refresh, and see the saved content locally and on the protected early deployment. Backend CI and frontend checks pass.

**Learn as needed:** JavaScript objects and arrays, TypeScript types, React components, props, state, forms, and routing.

## Phase 4: Add login and clinic permissions

**Outcome:** each user sees only the records and actions allowed for their role.

- [ ] Choose one established authentication approach and document it. Use maintained libraries or a managed identity provider; do not invent password hashing or token formats.
- [ ] Associate authenticated identities with seeded clinic memberships and doctor/staff roles.
- [ ] Add backend authorization checks to every record read and write, including requests using guessed IDs.
- [ ] Allow doctors to edit and approve notes. Allow staff to view and update assigned tasks; avoid exposing transcripts to staff by default.
- [ ] Allow staff to view and claim unassigned tasks in their own clinic. Enforce clinic membership on assignment and claiming in the backend.
- [ ] Add login, logout, expired-session behavior, and role-appropriate navigation.
- [ ] Remove the temporary development identity path from normal application operation.
- [ ] Test unauthenticated access, staff attempting doctor actions, and access across the two seeded clinics.

**Finish line:** clinic A cannot access clinic B's records, and staff cannot edit or approve clinical notes, even through direct API requests.

## Phase 5: Finish approval and follow-up without AI

**Outcome:** manually proposed tasks appear on the staff dashboard after approval.

- [ ] Add proposed follow-up tasks to the draft: description, optional due date, and optional assignee.
- [ ] Add approved task and audit-event tables with database constraints.
- [ ] Implement approval as one database transaction: verify the current draft version and role, save the approved snapshot, create tasks, and record the actor and timestamp.
- [ ] Make approval idempotent: repeated or concurrent approval of the same version returns the existing result without duplicate tasks. Enforce uniqueness in PostgreSQL.
- [ ] Make approved notes read-only for the MVP. Later corrections can use a separate amendment feature.
- [ ] Build the staff dashboard with assigned tasks and `open`, `in_progress`, and `done` states.
- [ ] Add an `Unassigned` clinic queue alongside `My tasks`. Approval places tasks with no assignee in this queue; claiming a task atomically assigns it to one eligible clinic user so concurrent claims cannot silently overwrite ownership.
- [ ] Test repeated approval, concurrent approval, stale draft approval, and rollback when task creation fails.
- [ ] Test visibility of unassigned tasks, same-clinic assignment, cross-clinic rejection, and competing claims.
- [ ] Before starting Phase 6, write five fictional evaluation transcripts with manually checked facts, evidence, and expected tasks: a straightforward visit, negation, an unspecified dose, no follow-up instruction, and ambiguous relative timing.

**Finish line:** approve a manual note with one assigned and one unassigned task; both appear in the appropriate staff queues and can be completed. Repeated approval creates no extras. Five checked transcripts are ready to guide AI schema design.

## Phase 6: Add AI drafting with evidence

**Outcome:** an AI-generated draft enters the same review workflow already working manually.

- [ ] Define a strict output schema for note sections, extracted facts, evidence references, and proposed tasks.
- [ ] Use the five prepared transcripts to check that the schema represents the expected facts, missing information, and tasks before integrating a model.
- [ ] Split the saved transcript into stable, numbered segments. Ask the model to reference segment IDs and exact supporting quotes.
- [ ] Add a backend provider adapter and keep the API key on the server.
- [ ] Instruct the model to treat transcript content as data, extract only documented information, preserve negation, and mark missing details as `not documented`.
- [ ] Validate output with Pydantic and check that cited segments and quotes exist in the saved transcript. Treat these checks as evidence-location validation, not proof that a claim is correct.
- [ ] Add a Generate Draft action and clickable evidence that highlights the supporting transcript text.
- [ ] Keep AI proposals editable and separate from approved tasks. Preserve the original generated draft alongside the doctor's reviewed version.
- [ ] Bind every evidence reference to the immutable transcript revision and generation that produced it. If the transcript changes, show the original source revision and mark the evidence as requiring review rather than linking it to the new text.
- [ ] Mark changed facts as `doctor-edited` and flag their original evidence for review. Do not present the original quote as verified support for the edited claim; retain it as historical evidence. If editing whole sections, conservatively invalidate evidence for all affected facts.
- [ ] Require the doctor to acknowledge flagged evidence before approval. Persist whether a fact is AI-extracted or doctor-edited and its evidence-review status in the approved snapshot; acknowledgement does not automatically prove the quote supports the changed claim.
- [ ] Before regeneration replaces an existing draft, show a confirmation or comparison and let the doctor retain the existing draft. Keep the previous version even when replacement is accepted.
- [ ] Keep unspecified doses and dates unspecified. Preserve relative timing such as `in two weeks`; show any calculated due date for doctor confirmation using the encounter date and clinic timezone.
- [ ] Add explicit handling for timeouts, provider failures, and invalid output, with a retry action that preserves the transcript and existing edits.
- [ ] Implement the Phase 2 generation acceptance rules: reject a returning result if the transcript changed, the draft changed, the encounter was approved, or a newer generation superseded the request. Recheck on confirmed replacement, not only when the response first arrives.
- [ ] Protect unsaved browser edits too: track the local edit revision and never automatically replace locally changed text with a returning generation.
- [ ] Test doctor edits with unchanged transcript, transcript edits, approval during generation, out-of-order responses, unsaved browser edits, cancelled replacement, and edited-fact evidence handling using controlled provider responses.

**Finish line:** a fictional transcript generates a draft with usable evidence links; the doctor can correct it and approve it through the existing workflow. Edited facts are clearly distinguished from original AI claims, and stale responses, regeneration, and failures never silently overwrite doctor work.

**Keep it small:** start with a bounded request and visible loading state. Add a durable background job only if measured response times or hosting limits require one. If added, persist job status and handle worker restarts and repeated submissions.

## Phase 7: Measure the behavior and polish the demo

**Outcome:** the project has evidence of reliability and honest AI results.

- [ ] Expand the five prepared fictional transcripts to 15-20 with manually reviewed expected facts, negations, evidence, and tasks.
- [ ] Include missing medication doses, no follow-up instruction, ambiguous dates, multiple follow-ups, contradictory statements, and transcript text that tries to instruct the model.
- [ ] Create a repeatable evaluation command and record the model, prompt version, dataset version, and run date.
- [ ] Report supported-fact precision, expected-fact recall, unsupported claims, evidence validity, and task extraction results. Define how each metric is scored.
- [ ] Record generation latency and failures separately from extraction quality; manually inspect semantic support rather than relying only on exact text matching.
- [ ] Add a Playwright test for login -> encounter -> draft review -> approval -> task completion, using deterministic AI responses in automated tests.
- [ ] Run live-model evaluations separately from CI so tests do not depend on provider availability or variable responses.
- [ ] Check error messages, keyboard navigation, empty states, and the full workflow on laptop and narrow screens.

**Finish line:** the automated workflow passes, and `docs/evaluation.md` reports actual results, known failures, and limitations without invented accuracy claims.

## Phase 8: Deploy and prepare interview material

**Outcome:** another person can run or try the project and understand your decisions.

- [ ] Finalize the existing backend container and document production migrations and seed commands.
- [ ] Review usage and budget settings on the hosting target selected in Phase 1.
- [ ] Update the existing deployment with the complete workflow and verify HTTPS, CORS settings, and server-side secrets.
- [ ] Make AI generation available only to authenticated demo users and add request/input limits to control usage.
- [ ] Add health checks and useful error logs without logging transcript text or secrets.
- [ ] Extend the existing CI with the main browser workflow and confirm backend tests, frontend type checks, and builds remain green.
- [ ] Verify permissions, migrations, approval behavior, and AI error handling on the deployed app.
- [ ] Document how fictional demo data is seeded and reset so one visitor's actions do not permanently break the walkthrough.
- [ ] Finish the README with screenshots, setup, architecture, data model, demo instructions, test commands, and known limitations.
- [ ] Write a short decisions document covering PostgreSQL, evidence links, human approval, duplicate-task prevention, and the choice of one backend.
- [ ] Document a few concrete examples of AI-assisted development: what was suggested, what you reviewed or changed, and how you verified it.
- [ ] Record a 2-3 minute walkthrough and prepare interview explanations of one bug, one trade-off, and one measured improvement.

**Finish line:** the deployed fictional workflow works end to end, setup is reproducible, checks pass, and the README links to the demo and evaluation report.

## Suggested working rhythm

1. Pick one unchecked task and describe its expected behavior before coding.
2. Implement the smallest useful change.
3. Run the relevant check and manually exercise the changed behavior.
4. Commit the working result and update this checklist.
5. Write down one thing learned or one decision worth discussing in an interview.

Prioritize understanding Python API design, SQL relationships and transactions, frontend state, authorization, and AI validation. Avoid learning every optional tool before building the first workflow.

## Explicitly deferred

- Audio recording and transcription.
- Real patient data, clinical deployment, or claims of regulatory compliance.
- Diagnosis, prescribing, treatment recommendations, or autonomous clinical actions.
- Billing, insurance, EHR integrations, and patient messaging.
- Multiple specialties, advanced analytics, and custom workflow builders.
- Vector databases, RAG, agent frameworks, microservices, Kubernetes, and model fine-tuning.

Revisit these only after the complete portfolio demo works and a concrete requirement justifies the extra work.
