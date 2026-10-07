"""MEDIUM DIAGNOSTIC tier: one question, a few arms, 4 seeds, 180-365 days.

Each named set compares a reference arm with the arms that answer one
question. Arms use the multiseed names plus an optional `@physiology`:

  thirst        v0-nothirst  vs v0                (thirst drive; 365 days by default)
  hunting       plant_diet   vs v1                (animal food and capture)
  interactions  no_interactions vs v1             (material interactions)
  learning      no_recall    vs v1                (place memory; reports repeated use,
                                                   transmission and food adoption)
  infant        v1           vs v1@reference-v2   (caregiving and energy budget)
  capacities    v0           vs v1
  integrity     v1-preg106   vs v1                (G10.6 behavioural/locomotion integrity)
  observation   v1-g104obs   vs v1                (G10.7a: only visible acts and consequences travel)
  memory        v1-nomem     vs v1                (G10.7a step 2: witnessed memory; outcomes must not differ)
  retention     v1-fifo      vs v1                (G10.7a step 2.5: what is kept; outcomes must not differ)

  python -m qualification.genesis.tiers diagnostic infant
  python -m qualification.genesis.tiers diagnostic custom --arms v1 v1@reference-v2 --days 365

Every run carries the smoke integrity checks; FAILs set exit status 1.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter

from qualification.genesis.smoke import report, run_many

SETS: dict[str, tuple[str, ...]] = {
    "thirst": ("v0-nothirst", "v0"),
    "hunting": ("plant_diet", "v1"),
    "interactions": ("no_interactions", "v1"),
    "learning": ("no_recall", "v1"),
    "infant": ("v1", "v1@reference-v2"),
    "capacities": ("v0", "v1"),
    "integrity": ("v1-preg106", "v1"),
    "observation": ("v1-g104obs", "v1"),
    "memory": ("v1-nomem", "v1"),
    "retention": ("v1-fifo", "v1"),
}
DIAGNOSTIC_SEEDS = ("agentus-demography-a", "agentus-demography-b", "agentus-demography-c", "agentus-demography-d")
DIAGNOSTIC_DAYS = 180
# Questions whose effect shows up late get a longer default.
SET_DAYS = {"thirst": 365}


def _sum(results: list[dict], getter) -> Counter:
    total: Counter = Counter()
    for r in results:
        if "crash" not in r:
            total.update(getter(r))
    return total


def arm_summary(arm: str, results: list[dict]) -> dict:
    ok = [r for r in results if "crash" not in r]
    n = max(1, len(ok))
    return {
        "arm": arm,
        "runs": len(results),
        "crashes": len(results) - len(ok),
        "alive_mean": round(sum(r["alive"] for r in ok) / n, 1),
        "adults_mean": round(sum(r["adults"] for r in ok) / n, 1),
        "births": sum(r["births"] for r in ok),
        "deaths_by_cause": {k: v for k, v in _sum(ok, lambda r: r["deaths_by_cause"]).items() if v},
        "death_context": dict(_sum(ok, lambda r: r["death_context"]).most_common(8)),
        "capture_attempts": sum(r["hunting"]["capture_attempts"] for r in ok),
        "kills": sum(r["hunting"]["captures"] for r in ok),
        "fresh_tissue_kg": round(sum(r["hunting"]["fresh_tissue_kg"] for r in ok), 3),
        "animals_end_mean": round(sum(r["hunting"]["animals_end"] for r in ok) / n, 1),
        "intake_kg_by_kind": {k: round(v, 1) for k, v in _sum(ok, lambda r: r["intake_kg_by_kind"]).items()},
        "food_kinds_valued": dict(_sum(ok, lambda r: r["food_kinds_valued"])),
        "interactions": dict(_sum(ok, lambda r: r["interaction_counts"])),
        "repeated_use": dict(_sum(ok, lambda r: r["repeated_use"])),
        "observed_transmissions": dict(_sum(ok, lambda r: r["observed_transmissions"])),
        "observed_food_adoptions": dict(_sum(ok, lambda r: r["observed_food_adoptions"])),
        "observed_ingestions": dict(_sum(ok, lambda r: r.get("observed_ingestions", {}))),
        "food_learned_after_observation": dict(_sum(ok, lambda r: r.get("food_learned_after_observation", {}))),
        "memory": [r.get("memory", {}) for r in ok],
        "fatigue_blocked_share": round(sum(r["fatigue_blocked_share"] for r in ok) / n, 3),
        "ledgers_valid": all(r["ledger_valid"] for r in ok),
        "max_element_balance_error": max((r["conservation"]["element_rel_error"] for r in ok), default=0.0),
        "fails": sum(len(r["checks"]["fail"]) for r in results),
        "warns": sum(len(r["checks"]["warn"]) for r in results),
    }


def print_comparison(summaries: list[dict], seeds: int, days: int) -> None:
    print(f"\n== DIAGNOSTIC: {seeds} seeds x {days} days, per arm (sums over seeds unless 'mean') ==")
    for s in summaries:
        print(f"\nARM {s['arm']}  runs {s['runs']}  crashes {s['crashes']}  FAIL {s['fails']}  warn {s['warns']}")
        print(f"  survivors mean {s['alive_mean']}  adults mean {s['adults_mean']}  births {s['births']}")
        print(f"  deaths by cause {s['deaths_by_cause']}")
        print(f"  death context  {s['death_context']}")
        print(f"  hunting: attempts {s['capture_attempts']} kills {s['kills']} fresh tissue {s['fresh_tissue_kg']} kg  animals at end (mean) {s['animals_end_mean']}")
        print(f"  intake kg {s['intake_kg_by_kind']}")
        print(f"  food kinds valued (living agents) {s['food_kinds_valued']}")
        print(f"  interactions {s['interactions']}")
        print(f"  repeated beneficial use {s['repeated_use']}")
        print(f"  observed transmissions {s['observed_transmissions']}")
        print(f"  food: legacy adoptions {s['observed_food_adoptions']}  ingestions seen {s['observed_ingestions']}  "
              f"learned by eating after seeing {s['food_learned_after_observation']}")
        for m in s["memory"]:
            if m.get("events_witnessed"):
                print(f"  memory: {m}")
        print(f"  fatigue-blocked agent-days {s['fatigue_blocked_share']:.0%}  ledgers valid {s['ledgers_valid']}  balance error {s['max_element_balance_error']:.1e}")
    ref = summaries[0]
    for s in summaries[1:]:
        dd = {k: s["deaths_by_cause"].get(k, 0) - ref["deaths_by_cause"].get(k, 0)
              for k in set(s["deaths_by_cause"]) | set(ref["deaths_by_cause"])}
        print(f"\nDELTA {s['arm']} - {ref['arm']}: survivors {s['alive_mean'] - ref['alive_mean']:+.1f}  "
              f"adults {s['adults_mean'] - ref['adults_mean']:+.1f}  births {s['births'] - ref['births']:+d}  "
              f"deaths {dict(sorted(dd.items()))}  kills {s['kills'] - ref['kills']:+d}")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="tiers diagnostic")
    p.add_argument("set", choices=sorted(SETS) + ["custom"])
    p.add_argument("--arms", nargs="*", help="override the set's arms (first is the reference)")
    p.add_argument("--seeds", nargs="*", default=list(DIAGNOSTIC_SEEDS))
    p.add_argument("--days", type=int, help=f"default {DIAGNOSTIC_DAYS} (thirst: 365)")
    p.add_argument("--parallel", type=int, default=4)
    p.add_argument("--json", help="write per-run results and summaries here")
    p.add_argument("--quiet-runs", action="store_true", help="skip the per-run lines")
    a = p.parse_args(argv)
    arms = tuple(a.arms) if a.arms else SETS.get(a.set, ())
    if not arms:
        p.error("custom needs --arms")
    a.days = a.days or SET_DAYS.get(a.set, DIAGNOSTIC_DAYS)
    t = time.perf_counter()
    jobs = [(seed, arm, a.days) for arm in arms for seed in a.seeds]
    results = run_many(jobs, a.parallel)
    status = 0
    if not a.quiet_runs:
        status = report(results, f"DIAGNOSTIC {a.set} runs")
    else:
        status = 1 if any(r["checks"]["fail"] for r in results) else 0
    summaries = [arm_summary(arm, [r for r in results if r["arm"] == arm]) for arm in arms]
    print_comparison(summaries, len(a.seeds), a.days)
    if a.json:
        with open(a.json, "w") as fh:
            json.dump({"runs": results, "summaries": summaries}, fh, indent=1, default=str)
    print(f"\nDIAGNOSTIC_SUMMARY: {json.dumps(summaries, sort_keys=True, default=str)}")
    print(f"diagnostic wall time {time.perf_counter() - t:.0f}s  RESULT: {'FAIL' if status else 'PASS'}", flush=True)
    return status


if __name__ == "__main__":
    sys.exit(main())
