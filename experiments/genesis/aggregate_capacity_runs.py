"""Aggregate per-run JSON files from run_agentus_capacity_multiseed.py --out.

Prints one CAPACITY_AGGREGATE line per arm and one CAPACITY_PAIRED line per
arm comparing it seed-by-seed against a reference arm. Read-only.
"""

from __future__ import annotations

import glob
import json
import sys
from collections import defaultdict


def _sum_maps(maps):
    out = defaultdict(float)
    for m in maps:
        for k, v in m.items():
            out[k] += float(v)
    return {k: round(v, 3) for k, v in sorted(out.items())}


def main(pattern: str, reference: str) -> int:
    runs = []
    for path in sorted(glob.glob(pattern)):
        with open(path, encoding="utf-8") as handle:
            runs.extend(json.load(handle))
    by_arm = defaultdict(dict)
    for r in runs:
        by_arm[r["arm"]][r["seed"]] = r
    for arm, seeds in sorted(by_arm.items()):
        rs = list(seeds.values())
        alive = [r["agentus_final"] for r in rs]
        lp = [r.get("learned_practice", {}) for r in rs]
        exploit_agents = defaultdict(int)
        for item in lp:
            for k, v in item.get("exploit_agent_counts", {}).items():
                exploit_agents[k] += v
        print("CAPACITY_AGGREGATE:", json.dumps({
            "arm": arm,
            "runs": len(rs),
            "alive_total": sum(alive),
            "alive_mean": round(sum(alive) / len(rs), 3),
            "extinct_runs": sum(1 for a in alive if a == 0),
            "runs_with_breeding_pair": sum(1 for r in rs if r["breeding_pairs_final"] > 0),
            "adults_total": sum(r["adults_final"] for r in rs),
            "births_total": sum(r["births"] for r in rs),
            "deaths_by_cause": _sum_maps(r["deaths_by_cause"] for r in rs),
            "intake_kg_by_kind": _sum_maps(r["intake_kg_by_kind"] for r in rs),
            "encounters": _sum_maps(r.get("encounters", {}) for r in rs),
            "agentus_kills": sum(r["animal_deaths_by_cause"].get("agentus", 0) for r in rs),
            "runs_animals_extinct": sum(1 for r in rs if r["availability"]["animals"]["final"] == 0),
            "material_events": _sum_maps(r["material_events"] for r in rs),
            "exploit_by_key": _sum_maps(item.get("exploit_by_key", {}) for item in lp),
            "exploit_agents_by_key": dict(sorted(exploit_agents.items())),
            "observed_transmissions": sum(sum(item.get("observed_transmissions", {}).values()) for item in lp),
            "observed_food_adoptions": _sum_maps(item.get("observed_food_adoptions", {}) for item in lp),
            "warmth_saved_kcal": round(sum(item.get("insulation_saving_kcal", 0.0) for item in lp), 1),
            "interaction_effort_kcal": round(sum(r["interaction_effort_kcal"] for r in rs)),
            "interaction_injury": round(sum(r["interaction_injury"] for r in rs), 3),
            "all_ledgers_valid": all(r["ledger_valid"] for r in rs),
            "alive_by_seed": {r["seed"]: r["agentus_final"] for r in sorted(rs, key=lambda r: r["seed"])},
        }, sort_keys=True), flush=True)
    ref = by_arm.get(reference, {})
    for arm, seeds in sorted(by_arm.items()):
        if arm == reference:
            continue
        common = sorted(set(seeds) & set(ref))
        diffs = [seeds[s]["agentus_final"] - ref[s]["agentus_final"] for s in common]
        print("CAPACITY_PAIRED:", json.dumps({
            "arm": arm, "reference": reference, "seeds": len(common),
            "better": sum(1 for d in diffs if d > 0), "worse": sum(1 for d in diffs if d < 0), "equal": sum(1 for d in diffs if d == 0),
            "mean_difference": round(sum(diffs) / len(diffs), 3) if diffs else None,
        }, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "v0"))
