# A 2-3 minute ClinicFlow walkthrough

Use fresh fictional demo data, a doctor session, and a second browser/session ready for staff. Keep the actual password out of recordings. Set `AI_MODE=demo` unless you are deliberately demonstrating a configured live provider, and explain the banner honestly.

| Time | Show | Explain |
| --- | --- | --- |
| 0:00-0:20 | Appointments and Avery Morgan's visit | "ClinicFlow helps a fictional dermatology clinic turn a visit into a reviewed note and staff follow-up. The workflow works manually too." |
| 0:20-0:45 | Transcript and Generate Draft | "This run uses labeled deterministic demo extraction so anyone can reproduce it without an API key. A live provider is a server-side configuration." |
| 0:45-1:15 | Candidate review, Apply, an evidence link | "Each quote points to a specific saved transcript revision. Finding the quote is a location check; the doctor still judges whether it supports the statement." |
| 1:15-1:40 | Edit a generated fact and review its evidence | "An edit is marked doctor-edited, and the old quote is retained as historical evidence. A returning generation cannot replace newer saved or unsaved edits." |
| 1:40-2:00 | Save and approve; show read-only state | "Approval saves the snapshot, creates tasks, and records the actor in one database transaction. Repeated requests cannot create duplicate tasks." |
| 2:00-2:25 | Staff session, Unassigned, claim, complete | "Staff receive actionable work after approval, without access to clinical transcripts. Unassigned tasks stay visible until claimed." |
| 2:25-2:45 | Evaluation report and test output | "These are measured local results. Deterministic fixture scores do not establish live-model quality. The docs list deployment and provider steps still requiring account setup." |

## Before recording

- Reset the seeded demo using the command in the README, then sign in again.
- Open the evaluation report and actual test output; never add an accuracy or latency claim that the report does not support.
- Close password managers, secret environment files, and unrelated browser tabs.
- Rehearse once on a laptop-size window, then capture the full workflow. The script is recording preparation, not evidence that a recording exists.

## Interview prompts

**One bug:** explain the race where a model starts from draft revision 3 and the doctor saves revision 4 before it returns. Transcript-only checking would lose the edit; both revisions and request identity must match at completion and apply. Show the regression test and rejection response.

**One trade-off:** approved notes are immutable in this MVP. That makes audit and retry behavior easier to explain, but later corrections require an explicit amendment feature.

**One measured improvement:** select a before/after result from the actual evaluation or regression report. For example, if a failing concurrency test was fixed, show the failing case and its passing run. Do not invent a quality increase or call deterministic demo precision a live-model improvement.

## Deliverable status

The narration/script is provided here. A human-narrated recording and published video link require recording and review. If an automated silent browser capture is included later, label it separately from a narrated walkthrough.

