# Engineering decisions

| Decision | Reason | Cost or limit |
| --- | --- | --- |
| PostgreSQL instead of a document database | Appointments, clinic membership, approved notes, and tasks have relationships; SQL constraints and transactions support approval directly. It also demonstrates SQL skills for the target role. | Schema changes require migrations, and a database must run locally. |
| Python/FastAPI backend | Builds on the author's Python knowledge and keeps validation, permissions, provider calls, and workflow logic in one place. | The React frontend adds TypeScript to learn and maintain. |
| React/Vite with one deployed backend | FastAPI already owns server behavior. A static client bundled into the container makes cookie authentication and deployment simpler. | Server-rendered public pages and independent frontend scaling are not needed by this internal dashboard. |
| Manual workflow before AI | The application remains useful when generation is disabled, slow, or wrong. AI produces another editable candidate in the existing workflow. | More initial product work than a transcript-to-text demonstration. |
| Session cookies and maintained password hashing | Opaque revocable sessions and Argon2 password hashing avoid custom token formats and browser-stored bearer tokens. | Sessions need database records and expiry/revocation handling. |
| Independent transcript and draft revisions | A doctor can edit the draft while a provider request is running without changing the transcript. Checking both prevents a lost update. | More explicit conflict states in the interface. |
| Candidate review before replacement | Preserves current work and gives doctors a deliberate regeneration choice. Apply rechecks all captured revisions. | Generation takes an extra review action. |
| Historical evidence rather than silent relinking | A quote must remain tied to the text that produced it. Edited facts are marked and original evidence needs review. | Evidence acknowledgements add work; quote existence still does not prove semantic support. |
| Human approval as one transaction | Only reviewed notes create actionable tasks. Snapshot, state, tasks, and audit either commit together or roll back. | Approved corrections need a future amendment workflow. |
| Database uniqueness plus idempotent approval | Double clicks and concurrent requests return one approval result without duplicate follow-up tasks. | API behavior must define which approved revision is a valid retry. |
| Explicit Unassigned queue | Optional assignment cannot make follow-up disappear. Atomic claiming resolves competing staff actions. | Someone must review and claim the queue. |
| Labeled deterministic demo mode | Anyone can run the workflow without an API key; browser tests are repeatable and avoid provider charges. | Fixture metrics are not live-model accuracy. Real evaluation remains a separate run. |
| One bounded provider request | The MVP can expose progress and preserve work without a separate durable job platform. | A process restart can interrupt a request; recovery must make retry possible. Measure before adding a queue. |

## Discussing the implementation in an interview

Use the repository and current test results as evidence. Explain one complete transaction, trace one request from React to PostgreSQL, and show a direct unauthorized API request being rejected. Be clear about which work was AI-assisted and which behavior you personally reviewed and tested.

Concrete development examples to inspect and reproduce:

- The initial delivery suggestion separated frontend hosting from the API. The implemented container bundles the built frontend into FastAPI so the cookie session has one production origin. Verify it with a production build, deep-link refresh, and the same browser workflow used against the development server.
- The stale-generation requirement was expanded from transcript-only checking to independent draft and transcript revisions. Review the capture/apply conditions and the regression where the doctor edits only the note while generation is pending. A passing test should prove the newer draft survives.
- The optional-assignee design exposed a task-discovery gap. The explicit Unassigned queue and atomic claim operation make unowned work visible and prevent concurrent staff claims from overwriting each other. Verify both dashboard visibility and a competing-claim test.

These examples describe decisions present in the build plan and implementation. Do not claim personal authorship of generated code, a production deployment, or a measured improvement without showing the corresponding review or result. Add your own review notes as you learn the code.

