# ClinicFlow

A fictional dermatology visit, from transcript to reviewed note to completed follow-up. Built as a software engineering portfolio project with **Python, FastAPI, PostgreSQL, React, and TypeScript**.

Doctors can write a note manually or request an evidence-linked draft, review changes, and approve it. Staff claim and complete the resulting tasks. Approval is transactional, stale saves are rejected, and an AI result cannot silently overwrite newer work.

**Demo mode works without an API key.** It uses explicitly labeled deterministic extraction, not a live model. `OPENAI_API_KEY` and `OPENAI_MODEL` are deliberately empty until you configure live generation.

**Hosted demo:** pending account setup and deployment verification. See [deployment steps](docs/deployment.md). [Evaluation results](docs/evaluation.md) distinguish automated fixture results from live-model quality.

## Run with Docker

Requires Docker Engine/Desktop with Docker Compose v2.

1. Copy `.env.example` to `.env`.
2. Set `POSTGRES_PASSWORD` to a long alphanumeric password and `DEMO_PASSWORD` to a separate password of at least 12 characters. Leave the AI key/model empty and keep `AI_MODE=demo`. Compose supplies `DATABASE_URL` internally, so that field may stay empty for this option.
3. Run from the project root:

```sh
docker compose up --build -d
docker compose run --rm seed
```

Open **http://localhost:8000**. The app container serves both the built frontend and `/api`; PostgreSQL persists in a named volume. `docker compose logs app` shows server logs. `docker compose down` stops the app while retaining the database.

## Develop locally

Requires Python 3.13, Node.js 22+, and PostgreSQL 17. PostgreSQL can be native or started with `docker compose up -d db` after setting `POSTGRES_PASSWORD` in `.env`.

Copy `.env.example` to `.env`, then set `DEMO_PASSWORD` and `DATABASE_URL`. For example, if your local-only PostgreSQL password is `localExample12345678`:

```dotenv
DATABASE_URL=postgresql+psycopg://clinicflow:localExample12345678@127.0.0.1:54329/clinicflow
DEMO_PASSWORD=localDemoExample12345678
```

These are sample local credentials; choose your own. Native PostgreSQL must already have the matching role/database. Compose creates them automatically. If a database password contains URL punctuation, percent-encode it in the connection URL; the Compose template expects an alphanumeric password.

On Windows PowerShell:

```powershell
./scripts/setup.ps1
./scripts/dev.ps1
```

On Linux/macOS:

```sh
sh scripts/setup.sh
sh scripts/dev.sh
```

Open **http://127.0.0.1:5173**. Vite proxies `/api` to FastAPI on port 8000. Stop the Windows servers with `./scripts/stop-dev.ps1`; on Linux/macOS use Ctrl+C. Logs stay under ignored `.local/`. The setup command installs dependencies, migrates the schema, and adds demo data without resetting existing work.

## Try the workflow

Use the `DEMO_PASSWORD` you configured for these fictional accounts:

| Account | Role | Clinic |
| --- | --- | --- |
| `doctor@clinicflow.demo` | Doctor | Willow Dermatology |
| `staff@clinicflow.demo` | Staff | Willow Dermatology |
| `doctor@other.demo` | Doctor | Second fictional clinic |
| `staff@other.demo` | Staff | Second fictional clinic |

1. Sign in as the Willow doctor and open Avery Morgan's appointment.
2. Inspect or edit the transcript, save it, then generate a draft.
3. Review the candidate, apply it, and click an evidence reference. Edit a fact to see the evidence-review requirement.
4. Review proposed tasks and approve the saved note. Approval freezes the note and releases its tasks.
5. Sign out, sign in as staff, claim a task from **Unassigned**, and move it to **Done**.

To restart the walkthrough, explicitly reset only the seeded fictional clinics:

```sh
docker compose run --rm seed python -m app.seed --reset
```

For native development, run `.venv/Scripts/python.exe -m app.seed --reset` from `backend/` using the absolute interpreter path or `../.venv/Scripts/python.exe`; Linux/macOS uses `../.venv/bin/python`. Reset removes saved visits/tasks for seeded clinics and invalidates their sessions. There is no public reset endpoint. [Walkthrough script](docs/walkthrough.md).

## Checks

Use an isolated PostgreSQL database with `test` in its name. Backend tests must never target a database containing work you want to retain.

```powershell
# From the repository root, after creating clinicflow_test in PostgreSQL:
$env:TEST_DATABASE_URL = 'postgresql+psycopg://clinicflow:YOUR_PASSWORD@127.0.0.1:54329/clinicflow_test'
Push-Location backend
../.venv/Scripts/python.exe -m pytest -q
Pop-Location
Push-Location frontend
npm run build
npx playwright install chromium
$env:DEMO_PASSWORD = 'YOUR_DEMO_PASSWORD'
npm run test:e2e
Pop-Location
```

Playwright needs a running API with fresh seeded data; it starts Vite automatically. If Vite is already running, set `PLAYWRIGHT_BASE_URL=http://127.0.0.1:5173`. Reset the dedicated demo before repeating tests that approve visits. Linux/macOS uses `.venv/bin/python` and `export NAME=value` for environment variables.

GitHub Actions runs PostgreSQL tests, the TypeScript production build, deterministic browser tests, and a Docker build. The workflow exists in the repository; a remote green run requires pushing it to GitHub. Run live-model evaluations separately using [the evaluation instructions](docs/evaluation.md).

## How it is built

```mermaid
flowchart LR
  UI[React + TypeScript] -->|HttpOnly session cookie| API[FastAPI]
  API --> DB[(PostgreSQL 17)]
  API --> AI[Demo adapter or live provider]
  DB --> Versions[Transcript revisions, draft history, audit events]
```

Clinic-owned records include users, patients, appointments, encounters, note versions, generated candidates, and approved tasks. The server enforces clinic and role checks on record IDs, verifies independent draft/transcript revisions, and performs approval in one database transaction. [Architecture and data model](docs/architecture.md) · [API contract](docs/api-contract.md) · [Engineering decisions](docs/decisions.md) · [Build plan](plan.md).

## Current boundaries

Only fictional data belongs in this demo. It extracts documented content and clinician-stated follow-up; it does not diagnose, prescribe, contact patients, or connect to an EHR. Evidence-location checks verify that a quote exists, not that it semantically proves a claim. Doctors must review every draft. Approved-note amendments, audio, live messaging, and production clinical compliance are outside this portfolio's scope.

AI secrets stay on the server. Live generation requires a configured provider/model; it is not silently substituted for the demo adapter. Deployment, host billing settings, and live-model measurement need your own external account setup; see the linked status documents for what has actually been verified.

