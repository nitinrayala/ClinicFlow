# Extraction evaluation

## What was measured

The checked-in run in `evaluation/results/demo.json` exercises 20 fictional transcripts using `demo:rules-v1`. This is a deterministic labeled-line parser, **not a language model**. It makes the application runnable without an API key. These results do not measure live AI accuracy.

Fixtures are in `evaluation/encounters.json`. Five baseline cases cover a normal visit, negation, missing dose, no follow-up, and ambiguous timing. The remaining cases add contradictory statements, family history, patient questions, free prose, whitespace, and instruction-like transcript content. Expected outputs were written before running the evaluation. Follow-up instructions count as stated-plan facts as well as task references.

## Reproduce

From the repository root, with backend dependencies installed:

```sh
python scripts/evaluate.py --mode demo
```

For a separately labeled live evaluation, set `OPENAI_API_KEY` and `OPENAI_MODEL` in the environment or `.env`, then run:

```sh
python scripts/evaluate.py --mode live --output evaluation/results/live.json
```

Live mode makes billable provider calls. Missing credentials cause an explicit failure before any call. No live evaluation has been performed yet; no live accuracy or response-time claim is made.

Each JSON report records UTC run time, mode/model, prompt version, dataset version and SHA-256, individual outputs, missing references, and latency. The CLI exits nonzero for provider failures. Reference mismatches remain visible rather than being hidden by an arbitrary passing threshold.

## Demo results

| Measure | Result | Definition |
| --- | --- | --- |
| Reference fact precision | 43/43 (100%) | Produced note facts matching a checked reference, divided by produced facts. |
| Reference fact recall | 43/45 (95.56%) | Matched reference facts divided by all expected note/plan facts. |
| Reference task precision | 6/6 (100%) | Proposed tasks matching a reference, divided by proposed tasks. |
| Reference task recall | 6/8 (75%) | Matched task references divided by expected tasks. |
| Evidence location validity | 49/49 (100%) | Quotes found in their identified source segments. |
| Provider/schema failures | 0/20 | Extraction or application validation failures. |
| Forbidden-phrase hits | 0 | Matches against the case-specific forbidden phrases. |

Reference matching ignores case and punctuation but does not accept paraphrases. It is a conservative regression metric, not semantic scoring. Latency is reported in the JSON as median and nearest-rank p95, excluding module import/startup and including extraction plus schema/evidence validation. Local parser timings are not an estimate of network model latency. Extraction metrics exclude failed requests; the failure rate is always reported separately.

## Source/output review and limitations

The implementation review compared all 43 generated facts and six proposed tasks to their fictional source text. All were copied from supporting passages; no new dose, product name, date, diagnosis, or treatment recommendation appeared in this run. This is an engineering review of a small synthetic dataset, not independent clinical validation. A quote existing in the transcript cannot by itself prove the claim is supported in context.

- **Case 05:** the conditional follow-up remains in the note, but the conservative demo parser suppresses the task because it contains `if`. A doctor can manually create the proposal after reviewing the condition. This is counted as a missed expected task.
- **Case 09:** the patient's antibiotic question remains a question and does not create a medication instruction. The parser places it in symptoms because it only recognizes line labels; this is an imperfect section classification that the text-match metric does not penalize.
- **Case 10:** the unlabeled prose produces no extraction. Two note references and one task reference are missed. Use labeled transcripts for the demo; free-form interpretation is the live adapter's intended role and still needs evaluation.
- **Cases 08 and 19:** these specific instruction-like lines are omitted. This does not establish general resistance to prompt injection or adversarial inputs.
- **Cases 02, 07, 12, 13, and 17:** negation, contradictory statements, family attribution, uncertainty, and past treatment are preserved verbatim. A live model could alter them, so these remain required live review cases.

Future live runs require manual review of paraphrases, unsupported claims, wrong section assignment, attribution, and missed actions. Keep the original references and report disagreements instead of changing the dataset to match the model. Human review and evidence flags in the application remain required regardless of evaluation scores.

## Workflow reliability

Database and browser tests cover permissions, concurrent approval, stale edits, task ownership, and generation/application conflicts separately from extraction evaluation. See `docs/verification.md` for commands and actual execution results. Those tests use PostgreSQL and deterministic provider responses; they do not prove a live cloud deployment or provider integration has run successfully.
