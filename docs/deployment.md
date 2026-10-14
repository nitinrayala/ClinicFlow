# Deployment and operations

The application ships as one container containing the React production build and FastAPI, connected to PostgreSQL 17. **Render is the selected hosting target. A hosted instance, billing controls, HTTPS behavior, and hosted workflow have not yet been verified.** No cloud account or provider key was supplied. The files below prepare the deployment; they do not create an account or invent a demo URL.

## Target and budget

The checked-in `render.yaml` uses a Singapore web service (`0.5c-512mb`) and managed database (`0.1c-256mb`). It selects one instance, disables automatic deployment and database storage growth, and uses a private database connection. Docker support, health checks, migrations, and secret prompts follow the [Render Blueprint reference](https://render.com/docs/blueprint-spec).

Pricing checked **2026-09-08**: the selected web compute is **US$7/month** and database compute **US$6/month**, before applicable storage, outbound bandwidth, build usage, and taxes. The template asks for 1 GB database storage. Review the actual creation estimate; this is a planning baseline, not a guaranteed total. [Render pricing](https://render.com/pricing).

Before creating resources, set the build-pipeline monthly spend limit in Workspace Settings. That limit controls extra pipeline minutes, not all hosting charges. Inspect Billing for compute and bandwidth usage; configure email failure notifications and any account alerts available to you. No billing setting has been applied by this project. [Build-pipeline spend limits](https://render.com/docs/build-pipeline), [billing and usage](https://render.com/docs/render-dashboard), [service notifications](https://render.com/docs/notifications).

## First release

1. Push the reviewed repository to your own GitHub repository and run its CI checks. The repository does not contain cloud credentials.
2. In Render, create a Blueprint from the repository and review the two paid resources before creating them.
3. Set `DEMO_PASSWORD` to a strong, private password and `ALLOWED_ORIGINS` to the exact HTTPS app URL, without a trailing slash. The URL is shown in the service dashboard. If the assigned hostname differs from your initial choice, correct it and redeploy.
4. Keep `AI_MODE=demo`, `COOKIE_SECURE=true`, and `APP_ENV=production`. Leave `OPENAI_API_KEY` and `OPENAI_MODEL` empty. `DATABASE_URL` is injected from the database resource. Use Render's secret environment values when adding the optional key later.
5. Deploy. The pre-deploy command runs `python -m alembic upgrade head`; the first-deploy hook runs `python -m app.seed`. Inspect the result of both. If seeding needs retrying, run the seed command in the web service Shell after migration succeeds.
6. Check `/api/health`, then run the checks below. Update the README demo link and the release checklist only after they pass.

During an early deployment without application authentication, host-level access protection would be required. This final template expects the implemented application login. Keep demo credentials private until the intended reviewer is ready; there is no anonymous demo login or generation shortcut.

The container listens on the host-provided `PORT`. The hosting proxy terminates HTTPS. UI assets and `/api` share one origin, so cookies do not need third-party settings. Additional origins must be explicitly listed; wildcard origins are not permitted in production. Directly exposed containers should not trust arbitrary forwarded headers: this launch command assumes the Render reverse proxy or a loopback-only local port.

## Release checks

Run the smoke tool from the repository root; it prompts for no credentials and reads the configured demo password from the environment:

```powershell
$env:DEMO_PASSWORD = 'YOUR_PRIVATE_DEMO_PASSWORD'
python scripts/smoke.py --base-url https://YOUR-APP.onrender.com
```

The smoke verifies health, no anonymous appointments access, doctor login/session, staff access restrictions, task access, and logout revocation. It avoids printing session values, transcripts, and connection strings. For the complete hosted browser flow against fresh fictional data:

```powershell
Push-Location frontend
$env:PLAYWRIGHT_BASE_URL = 'https://YOUR-APP.onrender.com'
npm run test:e2e
Pop-Location
```

Use the browser's network panel to confirm `Secure`, `HttpOnly`, and `SameSite` on the session cookie. Attempt a cross-clinic record URL with each doctor account and confirm rejection. Generate, review, edit, approve twice, and complete a task. Switch to a deliberately unconfigured live mode in an isolated test release to verify a useful error leaves saved work intact, then restore demo mode. Inspect host logs for health/migration failures without storing transcript text or secrets.

Hosted browser tests modify seeded demo visits and tasks. Reset that fictional demo before/after a test run; do not point the tests at a clinical or non-demo database.

## Seed, reset, and migrations

Commands below run in the container's working directory, `/app/backend`:

```sh
python -m alembic current
python -m alembic upgrade head
python -m app.seed
```

The seed command is repeatable. It adds missing fictional data without clearing reviewed work. `DEMO_PASSWORD` must be set before seeding. To deliberately restore the two seeded clinics for another walkthrough:

```sh
python -m app.seed --reset
```

Reset removes the seeded clinics' visits, notes, generation history, tasks, and sessions and then recreates their fictional data. Sign in again afterward. Run it between reviewers, not while someone is using the demo. There is no reset HTTP endpoint and reset does not run on ordinary application restarts. For Docker locally, use `docker compose run --rm seed python -m app.seed --reset`.

Migrations run once per release rather than during each web worker's startup. Before future destructive schema changes, back up and test restoration on a separate database. Prefer a forward corrective migration; rolling back a container does not reverse its database migration.

## Live provider setup

Set `AI_MODE=live`, add `OPENAI_API_KEY` and a supported `OPENAI_MODEL` in server environment settings, then redeploy. The repository intentionally supplies no key/model. Set a provider project usage budget in your provider account and run the separate live evaluation before making quality claims. Keep the labeled demo mode available when no key is configured.

Authenticated doctors alone can request generation. Default limits are 20 requests per user per hour, a 20,000-character transcript, up to 30 proposed tasks, and a 45-second provider timeout. Login attempts are limited to 10 per email/IP per minute. These defaults can be adjusted through the backend configuration; do not remove them to make a failing test pass.

## Verification record

| Release item | Current evidence |
| --- | --- |
| Container, Compose, host template | Committed source artifacts; see CI/local run output for execution status |
| External account and resource creation | Pending owner account setup |
| Host budget controls | Pending owner account access |
| Public demo URL and HTTPS | Pending deployment |
| Hosted migrations, permissions, approvals, provider failure | Pending hosted smoke/browser run |
| Live provider evaluation | Pending key/model; see `evaluation.md` |

