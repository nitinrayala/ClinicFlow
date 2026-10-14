"""Run reproducible fictional extraction evaluations; live calls are opt-in.

Usage: python scripts/evaluate.py --mode demo
       python scripts/evaluate.py --mode live --output evaluation/results/live.json
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))


def normalize(text: str) -> str:
    return re.sub(r"[^\w\s]", "", text.casefold()).strip()


def matching(actual: list[str], expected: list[str]) -> tuple[int, list[str], list[str]]:
    remaining = Counter(normalize(item) for item in expected)
    unmatched = []
    hits = 0
    for item in actual:
        key = normalize(item)
        if remaining[key]:
            remaining[key] -= 1
            hits += 1
        else:
            unmatched.append(item)
    missing = list(remaining.elements())
    return hits, unmatched, missing


def fraction(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 4) if denominator else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["demo", "live"], default="demo")
    parser.add_argument("--dataset", type=Path, default=ROOT / "evaluation/encounters.json")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    from app.ai import PROMPT_VERSION, ProviderFailure, extract, materialize, segments
    from app.config import get_settings

    settings = get_settings()
    settings.ai_mode = args.mode
    if args.mode == "live" and (not settings.openai_api_key or not settings.openai_model):
        print("Live evaluation requires OPENAI_API_KEY and OPENAI_MODEL; no calls were made.", file=sys.stderr)
        return 2
    raw = args.dataset.read_bytes()
    dataset = json.loads(raw)
    results = []
    totals = Counter()
    for case in dataset["cases"]:
        started = time.perf_counter()
        row = {"id": case["id"], "category": case["category"], "review_notes": case["notes"]}
        try:
            output, provider = extract(case["transcript"])
            # Exercise application schema and evidence-location validation as well as extraction.
            materialize(output, case["transcript"], 1, "evaluation")
            note_facts = [fact for section in (output.note.symptoms, output.note.history, output.note.findings, output.note.plan) for fact in section]
            tasks = output.proposed_tasks
            actual_facts = [fact.text for fact in note_facts]
            actual_tasks = [task.description for task in tasks]
            # Follow-up instructions are also legitimate stated-plan facts in the note.
            expected_facts = list(dict.fromkeys(case["facts"] + case["tasks"]))
            hits, unmatched, missing = matching(actual_facts, expected_facts)
            task_hits, task_unmatched, task_missing = matching(actual_tasks, case["tasks"])
            source = segments(case["transcript"])
            refs = [ref for item in [*note_facts, *tasks] for ref in item.evidence]
            valid_refs = sum(ref.segment_id in source and bool(ref.quote.strip()) and ref.quote in source[ref.segment_id] for ref in refs)
            # This is a mechanical support proxy, NOT an entailment/clinical correctness judgment.
            nonverbatim = [fact.text for fact in note_facts if not any(normalize(fact.text) in normalize(ref.quote) for ref in fact.evidence)]
            joined = "\n".join([*actual_facts, *actual_tasks]).casefold()
            forbidden = [phrase for phrase in case["forbidden"] if phrase.casefold() in joined]
            row.update(provider=provider, output=output.model_dump(), expected_facts=expected_facts,
                       fact_hits=hits, fact_reference_mismatches=unmatched, missing_facts=missing,
                       task_hits=task_hits, task_reference_mismatches=task_unmatched, missing_tasks=task_missing,
                       evidence_total=len(refs), evidence_valid=valid_refs, nonverbatim_claims_for_review=nonverbatim,
                       forbidden_phrase_hits=forbidden, status="ok")
            totals.update(fact_hits=hits, facts=len(note_facts), expected_facts=len(expected_facts),
                          task_hits=task_hits, tasks=len(tasks), expected_tasks=len(case["tasks"]),
                          evidence_valid=valid_refs, evidence_total=len(refs), forbidden_phrase_hits=len(forbidden),
                          nonverbatim_claims=len(nonverbatim))
        except ProviderFailure as error:
            row.update(status="failed", error=str(error))
            totals["failures"] += 1
        row["latency_ms"] = round((time.perf_counter() - started) * 1000, 3)
        results.append(row)
        print(f"{row['id']}: {row['status']} ({row['latency_ms']} ms)")

    latencies = sorted(row["latency_ms"] for row in results)
    report = {
        "run_at": datetime.now(timezone.utc).isoformat(), "mode": args.mode,
        "model": settings.openai_model if args.mode == "live" else "none (deterministic rules-v1)",
        "prompt_version": PROMPT_VERSION, "dataset_version": dataset["version"],
        "dataset_sha256": hashlib.sha256(raw).hexdigest(), "cases": len(results),
        "metrics": {
            "reference_fact_precision": fraction(totals["fact_hits"], totals["facts"]),
            "reference_fact_recall": fraction(totals["fact_hits"], totals["expected_facts"]),
            "reference_task_precision": fraction(totals["task_hits"], totals["tasks"]),
            "reference_task_recall": fraction(totals["task_hits"], totals["expected_tasks"]),
            "evidence_location_validity": fraction(totals["evidence_valid"], totals["evidence_total"]),
            "latency_median_ms": statistics.median(latencies),
            "latency_p95_ms": latencies[math.ceil(len(latencies)*0.95)-1],
            "failure_rate": totals["failures"] / len(results),
        }, "counts": dict(totals),
        "limitations": [
            "Demo mode is a deterministic parser, not an LLM, and its results do not measure live AI accuracy.",
            "Reference matching ignores case and punctuation but not paraphrases; it is a conservative reference metric.",
            "Quote-location validity does not prove semantic support, clinical correctness, or completeness.",
            "Failures are reported separately; extraction metrics include successful cases only.",
            "Unsupported claims require human review. Nonverbatim claims and reference mismatches are review queues, not unsupported-claim counts.",
            "The small synthetic set is a regression aid, not a representative clinical validation study.",
        ], "results": results,
    }
    destination = args.output or ROOT / f"evaluation/results/{args.mode}.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report["metrics"], indent=2))
    print(f"Report written: {destination}")
    return 1 if totals["failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
