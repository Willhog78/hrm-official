"""FAST SMOKE tier: a few short production runs with every mechanism on.

Default: 3 seeds x 75 days, arm `v1` (capacities, thirst, interactions,
learning, observation; production physiology). Runs in parallel, about a
minute in total. Exit status 1 if any FAIL check trips.

  python -m qualification.genesis.tiers smoke
  python -m qualification.genesis.tiers smoke --days 90 --arm v1@reference-v2
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor

from qualification.genesis.tier_observer import run_observed, unobserved_digest

SMOKE_SEEDS = ("agentus-demography-a", "agentus-demography-b", "agentus-g10-4-01")
SMOKE_DAYS = 75
SMOKE_ARM = "v1"


def _job(args: tuple) -> dict:
    if args[0] == "unobserved":
        return {"digest": unobserved_digest(*args[1:])}
    return run_observed(*args)


def run_many(jobs: list[tuple[str, str, int]], parallel: int) -> list[dict]:
    if parallel <= 1 or len(jobs) == 1:
        return [_job(j) for j in jobs]
    with ProcessPoolExecutor(max_workers=min(parallel, len(jobs))) as pool:
        return list(pool.map(_job, jobs))


def short_line(r: dict) -> str:
    if "crash" in r:
        return f"{r['arm']:<18} {r['seed']:<22} CRASH {r['crash']}"
    d = r["deaths_by_cause"]
    o = r["observer"]
    return (
        f"{r['arm']:<18} {r['seed']:<22} alive {r['alive']:>3}/{r['founders']:<3} births {r['births']:>3} "
        f"deaths e{d.get('energy', 0)}/w{d.get('dehydration', 0)}/i{d.get('injury', 0)}  "
        f"interactions {o.get('interactions', 0):>4} (no-op {o.get('noop_interactions', 0)}) "
        f"kills {o.get('kills', 0)} thirst-moves {o.get('thirst_moves', 0)}  "
        f"fatigue-blocked {r['fatigue_blocked_share']:.0%}  {r['seconds']}s"
    )


def report(results: list[dict], title: str) -> int:
    print(f"\n== {title} ==")
    fails = warns = 0
    for r in results:
        print(short_line(r))
        for line in r["checks"]["fail"]:
            print(f"    FAIL {line}")
        for line in r["checks"]["warn"]:
            print(f"    warn {line}")
        for ex in r.get("examples", [])[:5]:
            print(f"      e.g. {ex}")
        fails += len(r["checks"]["fail"])
        warns += len(r["checks"]["warn"])
    worst = max((r.get("conservation", {}).get("element_rel_error", 0.0) for r in results), default=0.0)
    print(f"ledgers valid: {all(r.get('ledger_valid') for r in results)}   max element balance error: {worst:.1e}")
    print(f"RESULT: {'FAIL' if fails else 'PASS'}  ({fails} fail, {warns} warn)")
    return 1 if fails else 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="tiers smoke")
    p.add_argument("--seeds", nargs="*", default=list(SMOKE_SEEDS))
    p.add_argument("--days", type=int, default=SMOKE_DAYS)
    p.add_argument("--arm", default=SMOKE_ARM)
    p.add_argument("--parallel", type=int, default=4)
    p.add_argument("--json", help="write full per-run results here")
    p.add_argument("--no-determinism", action="store_true",
                   help="skip re-running the first seed without the observer to compare ledgers")
    a = p.parse_args(argv)
    t = time.perf_counter()
    jobs: list[tuple] = [(s, a.arm, a.days) for s in a.seeds]
    if not a.no_determinism:
        # The observer must be invisible: same seed, same ledger without it.
        jobs.append(("unobserved", a.seeds[0], a.arm, a.days))
    results = run_many(jobs, a.parallel)
    plain = results.pop() if not a.no_determinism else None
    if plain is not None and "crash" not in results[0]:
        same = plain["digest"] == results[0]["ledger_digest"]
        print(f"determinism: observed and unobserved ledgers for {a.seeds[0]} {'IDENTICAL' if same else 'DIFFER'}")
        if not same:
            results[0]["checks"]["fail"].append("observer changed the run (ledger digest differs)")
    if a.json:
        with open(a.json, "w") as fh:
            json.dump(results, fh, indent=1, default=str)
    status = report(results, f"SMOKE {a.arm} {len(a.seeds)} seeds x {a.days} days")
    print(f"smoke wall time {time.perf_counter() - t:.0f}s", flush=True)
    return status


if __name__ == "__main__":
    sys.exit(main())
