"""Plant mass ledger (read-only): where edible plant mass comes from and goes.

Every change to the producer pools, by year, in kg:
  producer step (ecology/plants.py FLOW_OBSERVER): decomposition (detritus to
    soil), germination (seed to edible), growth (soil to edible or woody), fire
    (woody/loose/arranged to detritus), mortality (edible or woody to
    detritus), reproduction (edible to seed)
  animals: net change of each pool across the consumer step
  Agentus: net change of each pool across the Agentus step, with the plant
    tissue and seed they ate (capacity_stats) shown separately from handling

For each pool, opening + flows = closing; the residual (rounding at 1e-10 kg
per cell) is reported and must be ~0. `--control` runs the same seed, grid,
weather and plant rules with no animals and no Agentus. `--check-digest`
confirms the observed run's ledger digest equals an unobserved run's.

  python -m qualification.genesis.plant_ledger --years 5 --seeds agentus-demography-a
  python -m qualification.genesis.plant_ledger --years 10 --control
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

import hrm_genesis.runner as runner  # noqa: E402
from hrm_genesis import GenesisConfig, GenesisSimulation  # noqa: E402
from hrm_genesis.ecology import plants  # noqa: E402
from qualification.genesis.tier_observer import build_config  # noqa: E402

DEFAULT_SEEDS = ("agentus-demography-a", "agentus-demography-b", "agentus-demography-c", "agentus-demography-d")
POOLS = ("plant", "woody", "seed", "detritus", "loose_material", "arranged_material")
EDIBLE_FLOWS = {"germination": +1, "growth_edible": +1, "mortality_edible": -1, "reproduction": -1}


def pool_totals(producer_state: dict) -> dict[str, float]:
    out = Counter()
    for cell in producer_state["cells"]:
        for pool in POOLS:
            out[pool] += sum(float(v) for v in cell.get(f"{pool}_elements_kg", {}).values())
    return dict(out)


class PlantLedger:
    def __init__(self) -> None:
        self.flows: Counter = Counter()
        self._originals: list[tuple[object, str, object]] = []

    def install(self) -> None:
        ledger = self
        o_producers = runner.evolve_producers

        def observe(flow: str, kg: float) -> None:
            ledger.flows[flow] += float(kg)

        def evolve_producers(producer_state, *args, **kwargs):
            before = pool_totals(producer_state)
            out = o_producers(producer_state, *args, **kwargs)
            after = pool_totals(out[0])
            for pool in POOLS:
                ledger.flows[f"producer_step_net_{pool}"] += after[pool] - before[pool]
            return out

        def around(name: str, label: str, producers_arg: int, producers_out: int):
            original = getattr(runner, name)

            def wrapped(*args, **kwargs):
                before = pool_totals(args[producers_arg])
                out = original(*args, **kwargs)
                after = pool_totals(out[producers_out])
                for pool in POOLS:
                    ledger.flows[f"{label}_net_{pool}"] += after[pool] - before[pool]
                return out
            return original, wrapped

        self._originals.append((plants, "FLOW_OBSERVER", plants.FLOW_OBSERVER))
        plants.FLOW_OBSERVER = observe
        self._originals.append((runner, "evolve_producers", o_producers))
        runner.evolve_producers = evolve_producers
        for name, label, i, j in (("evolve_consumers", "animals", 1, 1),
                                  ("evolve_agentus_step", "agentus", 1, 1),
                                  ("evolve_humans", "agentus", 1, 1)):
            original, wrapped = around(name, label, i, j)
            self._originals.append((runner, name, original))
            setattr(runner, name, wrapped)

    def uninstall(self) -> None:
        for module, name, fn in reversed(self._originals):
            setattr(module, name, fn)
        self._originals.clear()


def control_config(seed: str, arm: str) -> GenesisConfig:
    """The same world with no animals and no Agentus (producers only)."""
    config = build_config(seed, arm)
    off = {k: False for k in ("consumer_ecology_enabled", "human_biology_enabled", "human_cognition_enabled",
                              "human_actions_enabled", "multi_population_enabled", "agentus_capacities_enabled",
                              "human_calibration_enabled", "agentus_thirst_enabled", "agentus_behavior_integrity_enabled",
                              "agentus_event_memory_enabled", "agentus_imitation_enabled", "agentus_following_enabled")
           if k in config.__dict__}
    return GenesisConfig(**{**config.__dict__, **off, "agentus_capacity_ablation": ""})


def run_ledger(seed: str, arm: str, years: int, control: bool) -> dict:
    started = time.perf_counter()
    config = control_config(seed, arm) if control else build_config(seed, arm)
    ledger = PlantLedger()
    ledger.install()
    try:
        sim = GenesisSimulation(config)
        tpy = int(config.ticks_per_year)
        opening = pool_totals(sim.ecology_state())
        yearly, monthly = [], []
        prev_eaten = Counter()
        for y in range(years):
            start = dict(pool_totals(sim.ecology_state()))
            ledger.flows = Counter()
            last = Counter()
            for day in range(tpy):
                sim.run(1)
                if day % 30 == 29 or day == tpy - 1:
                    f = ledger.flows
                    d = {k: f[k] - last[k] for k in ("growth_edible", "mortality_edible", "germination", "reproduction",
                                                    "animals_net_plant", "agentus_net_plant")}
                    last = Counter(f)
                    monthly.append({"day": y * tpy + day + 1, "edible_kg": round(pool_totals(sim.ecology_state())["plant"], 1),
                                    "growth": round(d["growth_edible"], 1), "germination": round(d["germination"], 1),
                                    "mortality": round(d["mortality_edible"], 1), "to_seed": round(d["reproduction"], 1),
                                    "animals": round(-d["animals_net_plant"], 2), "agentus": round(-d["agentus_net_plant"], 1)})
            end = pool_totals(sim.ecology_state())
            f = ledger.flows
            human_state = sim.human_state() if config.human_biology_enabled else {}
            eaten = Counter({k: float(v) for k, v in human_state.get("capacity_stats", {}).get("intake_kg_by_kind", {}).items()})
            solid = Counter({k: float(v) for k, v in human_state.get("capacity_stats", {}).get("solid_food_kg_by_kind", {}).items()})
            eaten_year = (eaten + solid) - prev_eaten
            prev_eaten = eaten + solid
            animals = sim.consumer_state().get("animals", []) if config.consumer_ecology_enabled else []
            residual = {pool: end[pool] - start[pool] - sum(f[f"{label}_net_{pool}"] for label in ("producer_step", "animals", "agentus"))
                        for pool in POOLS}
            producer_edible_residual = f["producer_step_net_plant"] - sum(sign * f[k] for k, sign in EDIBLE_FLOWS.items())
            yearly.append({
                "year": y + 1,
                "edible_start_kg": round(start["plant"], 1), "edible_end_kg": round(end["plant"], 1),
                "edible_in": {"growth": round(f["growth_edible"], 1), "germination": round(f["germination"], 1)},
                "edible_out": {"mortality_to_detritus": round(f["mortality_edible"], 1),
                               "reproduction_to_seed": round(f["reproduction"], 1),
                               "animals": round(-f["animals_net_plant"], 1),
                               "agentus": round(-f["agentus_net_plant"], 1)},
                "agentus_ate_kg": {k: round(v, 1) for k, v in sorted(eaten_year.items()) if v},
                "woody": {"growth": round(f["growth_woody"], 1), "mortality": round(f["mortality_woody"], 1),
                          "fire": round(f["fire_woody"], 1), "animals_net": round(f["animals_net_woody"], 1),
                          "agentus_net": round(f["agentus_net_woody"], 1), "end_kg": round(end["woody"], 1)},
                "seed": {"from_reproduction": round(f["reproduction"], 1), "germinated": round(f["germination"], 1),
                         "animals_net": round(f["animals_net_seed"], 1), "agentus_net": round(f["agentus_net_seed"], 1),
                         "end_kg": round(end["seed"], 1)},
                "detritus": {"in_mortality": round(f["mortality_edible"] + f["mortality_woody"], 1),
                             "in_fire": round(sum(v for k, v in f.items() if k.startswith("fire_")), 1),
                             "out_decomposition": round(f["decomposition"], 1),
                             "animals_net": round(f["animals_net_detritus"], 1), "agentus_net": round(f["agentus_net_detritus"], 1),
                             "end_kg": round(end["detritus"], 1)},
                "animals_alive": dict(Counter(a["species"] for a in animals)),
                "residual_kg": {k: round(v, 6) for k, v in residual.items()},
                "producer_edible_residual_kg": round(producer_edible_residual, 6),
            })
            print(f"PROGRESS plant-ledger {seed}{' control' if control else ''} year {y + 1}/{years}: "
                  f"edible {yearly[-1]['edible_start_kg']} -> {yearly[-1]['edible_end_kg']} kg  "
                  f"{time.perf_counter() - started:.0f}s", flush=True)
        return {"seed": seed, "arm": arm, "control": control, "years": years, "fingerprint": config.fingerprint()[:12],
                "ledger_digest": sim.ledger.digest(), "opening_kg": {k: round(v, 1) for k, v in opening.items()},
                "yearly": yearly, "monthly_edible_kg": monthly, "seconds": round(time.perf_counter() - started, 1)}
    finally:
        ledger.uninstall()


def unobserved_digest(seed: str, arm: str, days: int, control: bool) -> str:
    sim = GenesisSimulation(control_config(seed, arm) if control else build_config(seed, arm))
    sim.run(days)
    return sim.ledger.digest()


def _job(args):
    return run_ledger(*args)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="plant_ledger")
    p.add_argument("--seeds", nargs="*", default=list(DEFAULT_SEEDS))
    p.add_argument("--arm", default="v1")
    p.add_argument("--years", type=int, default=5)
    p.add_argument("--control", action="store_true", help="no animals and no Agentus")
    p.add_argument("--parallel", type=int, default=1)
    p.add_argument("--json")
    p.add_argument("--check-digest", action="store_true")
    a = p.parse_args(argv)
    jobs = [(s, a.arm, a.years, a.control) for s in a.seeds]
    if a.parallel <= 1:
        results = [_job(j) for j in jobs]
    else:
        with ProcessPoolExecutor(max_workers=a.parallel) as pool:
            results = list(pool.map(_job, jobs))
    status = 0
    for r in results:
        print(f"\n=== plant ledger {r['seed']} {'CONTROL (no animals, no Agentus)' if r['control'] else r['arm']} "
              f"fp {r['fingerprint']} {r['seconds']}s  opening {r['opening_kg']}")
        for y in r["yearly"]:
            print(f"  y{y['year']}: edible {y['edible_start_kg']} -> {y['edible_end_kg']} kg | in {y['edible_in']} | out {y['edible_out']}"
                  f" | Agentus ate {y['agentus_ate_kg']} | animals {y['animals_alive']}")
            print(f"       woody {y['woody']}  seed {y['seed']}")
            print(f"       detritus {y['detritus']}  residual {y['residual_kg']}  producer-edible residual {y['producer_edible_residual_kg']}")
            worst = max([abs(v) for v in y["residual_kg"].values()] + [abs(y["producer_edible_residual_kg"])])
            if worst > 1e-3 * max(1.0, y["edible_start_kg"]):
                print(f"  RESIDUAL TOO LARGE: {worst}")
                status = 1
        print("  month-end edible kg | edible flows over the month (kg): growth germination mortality to_seed animals agentus")
        for m in r["monthly_edible_kg"]:
            print(f"    day {m['day']:>5}: {m['edible_kg']:>10} | {m['growth']:>10} {m['germination']:>9} {m['mortality']:>10} "
                  f"{m['to_seed']:>9} {m['animals']:>7} {m['agentus']:>7}")
        if a.check_digest:
            same = unobserved_digest(r["seed"], r["arm"], r["years"] * 365, r["control"]) == r["ledger_digest"]
            print(f"  ledger non-causal: {'IDENTICAL' if same else 'DIFFERENT'} digest")
            status = status or (0 if same else 1)
    if a.json:
        Path(a.json).write_text(json.dumps(results, indent=1))
    print(f"\nRESULT: {'FAIL' if status else 'PASS'}")
    return status


if __name__ == "__main__":
    sys.exit(main())
