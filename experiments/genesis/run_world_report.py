"""Daily-world report: families, animals and learned behaviour, by year.

Runs the production configuration (arm `v1` by default; any tier arm works)
with no observer, and reads state once per simulated year. Nothing is tuned or
injected.

  python experiments/genesis/run_world_report.py --years 5 --json out.json
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for extra in (ROOT / "src", ROOT, ROOT / "experiments" / "genesis"):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

from hrm_genesis import GenesisSimulation  # noqa: E402
from qualification.genesis.tier_observer import build_config  # noqa: E402

SEEDS = ("agentus-demography-a", "agentus-demography-b", "agentus-demography-c", "agentus-demography-d")


def _mass(elements: dict) -> float:
    return sum(float(v) for v in elements.values())


def run(seed: str, arm: str, years: int) -> dict:
    started = time.perf_counter()
    sim = GenesisSimulation(build_config(seed, arm))
    year = int(sim.config.ticks_per_year)
    profile = sim.human_state()["physiology_profile"]
    maturity = int(profile["maturity_ticks"])
    independent = int(profile["independent_feeding_age_ticks"])
    born: dict[str, int] = {}
    died: dict[str, tuple[int, str]] = {}
    seen_records: set[str] = set()
    yearly = []
    prev_stats: dict = {}
    prev_consumers = {"births": 0, "deaths": Counter()}
    for y in range(years):
        alive_stage = Counter()
        for day in range(year):
            sim.run(1)
            epoch = y * year + day
            h = sim.human_state()
            for p in h["humans"]:
                if int(p["age_ticks"]) <= 1 and p["id"] not in born and p.get("generation", 0) > 0:
                    born[p["id"]] = epoch
            for r in h.get("death_records", []):
                if r["id"] not in seen_records:
                    seen_records.add(r["id"])
                    died[r["id"]] = (int(r["epoch"]), r["cause"])
            if day == year - 1:
                for p in h["humans"]:
                    a = int(p["age_ticks"])
                    alive_stage["adult" if a >= maturity else ("juvenile" if a >= independent else "dependent")] += 1
        h = sim.human_state()
        st = h.get("capacity_stats", {})
        c = sim.consumer_state()
        cdeaths = Counter({k: int(v) for k, v in c.get("cumulative_deaths_by_cause", {}).items()})
        people = h["humans"]
        def delta(key):
            return round(float(st.get(key, 0.0)) - float(prev_stats.get(key, 0.0)), 3)
        def delta_map(key):
            now, before = Counter(st.get(key, {})), Counter(prev_stats.get(key, {}))
            return {k: round(v, 3) for k, v in (now - before).items() if v}
        deaths_this_year = Counter()
        for pid, (ep, cause) in died.items():
            if y * year <= ep < (y + 1) * year:
                deaths_this_year[cause] += 1
        yearly.append({
            "year": y + 1,
            "alive": alive_stage.get("adult", 0) + alive_stage.get("juvenile", 0) + alive_stage.get("dependent", 0),
            "alive_by_stage": dict(alive_stage),
            "births": sum(1 for pid, ep in born.items() if y * year <= ep < (y + 1) * year),
            "deaths": dict(deaths_this_year),
            "max_generation": max((int(p.get("generation", 0)) for p in people), default=0),
            "solid_food_outcomes": delta_map("solid_food_outcomes"),
            "solid_food_kg": delta_map("solid_food_kg_by_kind"),
            "intake_kg_by_kind": delta_map("intake_kg_by_kind"),
            "captures": delta("captures"),
            "predator_attacks_on_agentus": int(h.get("predator_attack_events", 0)) - int(prev_stats.get("_attacks", 0)),
            "imitation_tries": sum(delta_map("imitation_tries").values()),
            "imitation_paid": sum(delta_map("imitation_paid").values()),
            "follow_days": delta("follow_days"),
            "repeated_use": delta_map("exploit_by_key"),
            "insulation_saving_kcal": delta("insulation_saving_kcal"),
            "food_kinds_valued_by_living": dict(Counter(k for p in people for k, v in p.get("cognition", {}).get("food_values", {}).items() if float(v) > 0)),
            "positive_acts_living": dict(Counter(k for p in people for k, e in p.get("cognition", {}).get("affordance_values", {}).items() if float(e["v"]) > 0).most_common(6)),
            "worn_objects": sum(1 for o in h.get("objects", []) if o.get("worn")),
            "objects": len(h.get("objects", [])),
            "animals": dict(Counter(a["species"] for a in c["animals"])),
            "animal_births": int(c.get("cumulative_births", 0)) - prev_consumers["births"],
            "animal_deaths": {k: v for k, v in (cdeaths - prev_consumers["deaths"]).items() if v},
            "edible_plant_t": round(sum(_mass(cell["plant_elements_kg"]) for cell in sim.ecology_state()["cells"]) / 1000.0, 1),
        })
        prev_stats = {**{k: (dict(v) if isinstance(v, dict) else v) for k, v in st.items()}, "_attacks": int(h.get("predator_attack_events", 0))}
        prev_consumers = {"births": int(c.get("cumulative_births", 0)), "deaths": cdeaths}
    end = years * year
    survival = {}
    for age_days, label in ((365, "to_1y"), (730, "to_2y"), (1825, "to_5y")):
        eligible = [pid for pid, ep in born.items() if ep + age_days <= end]
        survived = [pid for pid in eligible if pid not in died or died[pid][0] >= born[pid] + age_days]
        survival[label] = (len(survived), len(eligible))
    child_deaths = Counter(died[pid][1] for pid in born if pid in died)
    return {"seed": seed, "arm": arm, "years": years, "fingerprint": sim.config.fingerprint()[:12],
            "ledger_valid": sim.ledger.verify_chain(), "yearly": yearly, "child_survival": survival,
            "child_deaths_by_cause": dict(child_deaths), "births_total": len(born),
            "seconds": round(time.perf_counter() - started, 1)}


def _job(args):
    return run(*args)


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--years", type=int, default=5)
    p.add_argument("--arm", default="v1")
    p.add_argument("--seeds", nargs="*", default=list(SEEDS))
    p.add_argument("--parallel", type=int, default=4)
    p.add_argument("--json")
    a = p.parse_args(argv)
    with ProcessPoolExecutor(max_workers=a.parallel) as pool:
        results = list(pool.map(_job, [(s, a.arm, a.years) for s in a.seeds]))
    for r in results:
        print(f"\n=== {r['seed']} {r['arm']} fp {r['fingerprint']} ledger {'valid' if r['ledger_valid'] else 'INVALID'} {r['seconds']}s")
        print(f"  births {r['births_total']}  child survival {r['child_survival']}  child deaths {r['child_deaths_by_cause']}")
        for y in r["yearly"]:
            print(f"  y{y['year']}: alive {y['alive']} {y['alive_by_stage']} births {y['births']} deaths {y['deaths']} gen {y['max_generation']} | "
                  f"solid food {y['solid_food_outcomes']} kg {y['solid_food_kg']} | animals {y['animals']} (+{y['animal_births']} {y['animal_deaths']}) "
                  f"captures {y['captures']} attacks {y['predator_attacks_on_agentus']} | plants {y['edible_plant_t']} t")
            print(f"       learned: foods {y['food_kinds_valued_by_living']} positive acts {y['positive_acts_living']} repeated {y['repeated_use']} "
                  f"imitation {y['imitation_tries']}/{y['imitation_paid']} follow {y['follow_days']} warmth {y['insulation_saving_kcal']} worn {y['worn_objects']} objects {y['objects']}")
    if a.json:
        Path(a.json).write_text(json.dumps(results, indent=1))
    ok = all(r["ledger_valid"] for r in results)
    print(f"\nRESULT: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
