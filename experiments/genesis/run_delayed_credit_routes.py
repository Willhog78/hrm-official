"""Delayed-credit routes over two years (imitation audit, 2026-10-08).

Preparation acts can only pay later: through warmth saved by a worn surface
(credit_worn_benefit) or through food eaten from a capture or cut. This reads
the production counters at the end of 730-day runs; it changes nothing.

  python experiments/genesis/run_delayed_credit_routes.py
"""
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "src"), str(ROOT), str(ROOT / "experiments" / "genesis")]

def run(args):
    seed, arm = args
    from hrm_genesis import GenesisSimulation
    from qualification.genesis.tier_observer import build_config
    sim = GenesisSimulation(build_config(seed, arm)); sim.run(730)
    h = sim.human_state(); st = h.get("capacity_stats", {})
    objs = h.get("objects", [])
    pos = sum(1 for p in h["humans"] for k, e in p.get("cognition", {}).get("affordance_values", {}).items() if float(e["v"]) > 0)
    return {"seed": seed, "arm": arm,
            "insulation_saving_kcal": round(st.get("insulation_saving_kcal", 0.0), 1),
            "captures": st.get("captures", 0), "fresh_tissue_eaten_kg": round(st.get("intake_kg_by_kind", {}).get("fresh_tissue", 0.0), 3),
            "worn_objects_end": sum(1 for o in objs if o.get("worn")), "surfaces_end": sum(1 for o in objs if o.get("material") == "surface"),
            "objects_end": len(objs), "positive_affordance_values_living": pos,
            "repeated_use": st.get("exploit_by_key", {}), "interaction_effort_kcal": round(st.get("interaction_effort_kcal", 0.0), 1)}

if __name__ == "__main__":
    jobs = [(s, a) for a in ("v1", "v1@reference-v2") for s in ("agentus-demography-a", "agentus-demography-b", "agentus-demography-c", "agentus-demography-d")]
    with ProcessPoolExecutor(4) as pool:
        for r in pool.map(run, jobs):
            print(json.dumps(r))
