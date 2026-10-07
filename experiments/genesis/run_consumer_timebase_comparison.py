"""Consumer timebase comparison (D2 units correction).

Runs the Agentus world's ecology (16x16, material scale 1000, producers and
consumers, no Agentus) for whole years at 12 ticks/year and at 365 ticks/year,
the latter under "per-tick-legacy" and "elapsed-time-v1". Trajectories are not
expected to match (weather, plants and movement are per tick); per-year
quantities are compared: animals alive, births, deaths by cause, mean energy
and water state, and element and water balance.

  python experiments/genesis/run_consumer_timebase_comparison.py --years 5 --json out.json
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
for extra in (ROOT / "src", ROOT):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

from hrm_genesis import GenesisConfig, GenesisSimulation  # noqa: E402
from hrm_genesis.ecology.animals import consumer_element_totals, consumer_water_total_kg  # noqa: E402
from hrm_genesis.ecology.plants import ecology_element_totals  # noqa: E402
from hrm_genesis.ecology.traits import trait_for  # noqa: E402
from hrm_genesis.matter.pools import total_elements, total_water  # noqa: E402

ARMS = (("monthly", 12, "elapsed-time-v1"), ("daily-legacy", 365, "per-tick-legacy"), ("daily-elapsed", 365, "elapsed-time-v1"))
SEEDS = ("agentus-demography-a", "agentus-demography-b", "agentus-demography-c")


def _balance(sim: GenesisSimulation) -> tuple[float, float]:
    matter = sim.matter_state()
    parts = (total_elements(matter["cells"]), ecology_element_totals(sim.ecology_state()),
             consumer_element_totals(sim.consumer_state()))
    initial = {k: float(v) for k, v in matter["initial_elements_kg"].items()}
    symbols = sorted(set(initial).union(*parts))
    element = max(abs(sum(p.get(s, 0.0) for p in parts) - initial.get(s, 0.0)) for s in symbols) / max(1.0, sum(initial.values()))
    stored = total_water(matter["cells"]) + consumer_water_total_kg(sim.consumer_state())
    expected = float(matter["initial_water_kg"]) + float(matter["water_input_kg"]) - float(matter["water_output_kg"])
    return element, abs(stored - expected) / max(1.0, expected)


def run(seed: str, arm: str, tpy: int, timebase: str, years: int) -> dict:
    started = time.perf_counter()
    sim = GenesisSimulation(GenesisConfig(
        master_seed=seed, world_width=16, world_height=16, ticks_per_year=tpy, material_scale_factor=1000.0,
        producer_ecology_enabled=True, consumer_ecology_enabled=True, consumer_timebase=timebase))
    per_year = []
    births0, deaths0 = 0, Counter()
    for year in range(years):
        alive_ticks = Counter()
        energy_sum = water_frac_sum = 0.0
        samples = 0
        for _ in range(tpy):
            sim.run(1)
            animals = sim.consumer_state()["animals"]
            for a in animals:
                alive_ticks[a["species"]] += 1
                energy_sum += float(a["energy"])
                water_frac_sum += float(a["body_water_kg"]) / trait_for(a["species"]).water_capacity_kg
            samples += len(animals)
        c = sim.consumer_state()
        births = int(c.get("cumulative_births", 0))
        deaths = Counter({k: int(v) for k, v in c.get("cumulative_deaths_by_cause", {}).items()})
        per_year.append({
            "year": year + 1,
            "mean_alive": {k: round(v / tpy, 2) for k, v in sorted(alive_ticks.items())},
            "end_alive": dict(Counter(a["species"] for a in c["animals"])),
            "births": births - births0,
            "deaths": {k: v for k, v in (deaths - deaths0).items() if v},
            "mean_energy": round(energy_sum / max(1, samples), 3),
            "mean_water_fraction": round(water_frac_sum / max(1, samples), 3),
        })
        births0, deaths0 = births, deaths
    element, water = _balance(sim)
    return {"seed": seed, "arm": arm, "ticks_per_year": tpy, "timebase": timebase, "years": years,
            "fingerprint": sim.config.fingerprint()[:12], "ledger_valid": sim.ledger.verify_chain(),
            "element_rel_error": element, "water_rel_error": water, "per_year": per_year,
            "seconds": round(time.perf_counter() - started, 1)}


def _job(args):
    return run(*args)


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--years", type=int, default=5)
    p.add_argument("--seeds", nargs="*", default=list(SEEDS))
    p.add_argument("--parallel", type=int, default=4)
    p.add_argument("--json")
    a = p.parse_args(argv)
    jobs = [(seed, arm, tpy, tb, a.years) for arm, tpy, tb in ARMS for seed in a.seeds]
    with ProcessPoolExecutor(max_workers=a.parallel) as pool:
        results = list(pool.map(_job, jobs))
    status = 0
    for r in results:
        ok = r["ledger_valid"] and r["element_rel_error"] < 1e-6 and r["water_rel_error"] < 1e-6
        status = status or (0 if ok else 1)
        print(f"\n{r['seed']} {r['arm']:14s} fp {r['fingerprint']} ledger {'valid' if r['ledger_valid'] else 'INVALID'} "
              f"balance elements {r['element_rel_error']:.1e} water {r['water_rel_error']:.1e}  {r['seconds']}s")
        for y in r["per_year"]:
            print(f"  y{y['year']} mean alive {y['mean_alive']}  end {y['end_alive']}  births {y['births']:3d}  "
                  f"deaths {y['deaths']}  energy {y['mean_energy']}  water {y['mean_water_fraction']}")
    print("\n== per arm, summed over seeds ==")
    for arm, _, _ in ARMS:
        rs = [r for r in results if r["arm"] == arm]
        births = [sum(r["per_year"][i]["births"] for r in rs) for i in range(a.years)]
        deaths = Counter()
        for r in rs:
            for y in r["per_year"]:
                deaths.update(y["deaths"])
        end = Counter()
        for r in rs:
            end.update(r["per_year"][-1]["end_alive"])
        print(f"{arm:14s} births per year {births}  deaths {dict(deaths)}  alive at end {dict(end)}")
    if a.json:
        Path(a.json).write_text(json.dumps(results, indent=1))
    print(f"RESULT: {'FAIL' if status else 'PASS'}")
    return status


if __name__ == "__main__":
    sys.exit(main())
