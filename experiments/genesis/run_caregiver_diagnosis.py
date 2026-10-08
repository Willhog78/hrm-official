"""Read-only diagnosis of caregiver provisioning and dependent deaths.

For every dependent or weaning child, each day records whether its caregiver
was alive and in the same cell, the caregiver's energy and water, and what was
actually transferred. Every child death is classified by its immediate
provisioning context. Nursing mothers' daily energy balance is tracked too.

Wrappers only record what biology already computes and return its results
unchanged. Nothing here reaches the agents.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict

import hrm_genesis.human.biology as biology
from hrm_genesis import GenesisConfig, GenesisSimulation

SEEDS = ["agentus-demography-a", "agentus-demography-b", "agentus-demography-c", "agentus-demography-d"]


def config(seed: str, **overrides) -> GenesisConfig:
    base = dict(
        master_seed=seed, world_width=16, world_height=16, ticks_per_year=365,
        producer_ecology_enabled=True, consumer_ecology_enabled=True, human_biology_enabled=True,
        human_cognition_enabled=True, human_actions_enabled=True, multi_population_enabled=True,
        material_scale_factor=1000.0, human_calibration_enabled=True,
    )
    base.update(overrides)
    return GenesisConfig(**base)


def run(seed: str, days: int, overrides: dict) -> dict:
    transfers: dict[str, dict] = {}
    original = biology._provision_dependent

    def provision(child, caregiver, profile, *args, **kwargs):
        energy_before = float(child["energy"])
        caregiver_energy = None if caregiver is None else float(caregiver["energy"])
        result = original(child, caregiver, profile, *args, **kwargs)
        transfers[str(child["id"])] = {
            "caregiver": None if caregiver is None else str(caregiver["id"]),
            "co_located": caregiver is not None and (int(child["x"]), int(child["y"])) == (int(caregiver["x"]), int(caregiver["y"])),
            "caregiver_energy_before": caregiver_energy,
            "energy_received": float(child["energy"]) - energy_before,
            "dependence": float(profile.get("caregiver_dependence", 0.0)),
            "child_basal": float(profile["basal_energy_kcal_per_tick"]),
        }
        return result

    biology._provision_dependent = provision
    try:
        sim = GenesisSimulation(config(seed, **overrides))
        profile = sim.human_state()["physiology_profile"]
        windows: dict[str, list] = defaultdict(list)
        child_deaths = []
        counts = Counter()
        mother_days = Counter()
        for _ in range(days):
            transfers.clear()
            before = sim.human_state()
            sim.run(1)
            after = sim.human_state()
            alive = {str(p["id"]) for p in after["humans"]}
            for pid, t in transfers.items():
                if t["dependence"] <= 0.0:
                    continue
                windows[pid].append(t)
                del windows[pid][:-10]
                counts["dependent_days"] += 1
                counts["caregiver_absent_days"] += t["caregiver"] is None
                counts["caregiver_elsewhere_days"] += t["caregiver"] is not None and not t["co_located"]
                if t["co_located"]:
                    counts["co_located_days"] += 1
                    if t["energy_received"] < 0.5 * t["dependence"] * float(profile["nursing_energy_kcal_per_tick"]):
                        counts["co_located_but_underfed_days"] += 1
                    if t["caregiver_energy_before"] is not None and t["caregiver_energy_before"] <= float(profile["basal_energy_kcal_per_tick"]) * 1.5:
                        counts["caregiver_near_energy_floor_days"] += 1
            nursing_mothers = {t["caregiver"] for t in transfers.values() if t["caregiver"] and t["co_located"] and t["dependence"] > 0.0}
            for person in after["humans"]:
                if str(person["id"]) in nursing_mothers:
                    mother_days["days"] += 1
                    mother_days["energy_sum"] += float(person["energy"])
                    mother_days["below_one_day_reserve"] += float(person["energy"]) < float(profile["basal_energy_kcal_per_tick"])
            seen = {r["id"] for r in before.get("death_records", [])}
            for record in after.get("death_records", []):
                if record["id"] in seen or str(record["id"]) not in windows:
                    continue
                w = windows[str(record["id"])]
                last = w[-1] if w else {}
                if not last.get("caregiver"):
                    context = "no_caregiver"
                elif not last.get("co_located"):
                    context = "caregiver_alive_but_elsewhere"
                elif last.get("caregiver_energy_before") is not None and last["caregiver_energy_before"] <= float(profile["basal_energy_kcal_per_tick"]) * 1.5:
                    context = "caregiver_present_at_energy_floor"
                else:
                    context = "caregiver_present_with_reserve"
                person = next(p for p in before["humans"] if str(p["id"]) == str(record["id"]))
                child_deaths.append({
                    "cause": record["cause"], "context": context, "age_days": int(person["age_ticks"]),
                    "last_days": [{k: (round(v, 1) if isinstance(v, float) else v) for k, v in d.items()} for d in w[-4:]],
                })
        final = sim.human_state()
    finally:
        biology._provision_dependent = original
    return {
        "seed": seed, "overrides": overrides, "alive": len(final["humans"]), "births": final["cumulative_births"],
        "deaths_by_cause": final["cumulative_deaths_by_cause"],
        "dependent_day_counts": dict(counts),
        "nursing_mother_days": mother_days["days"],
        "nursing_mother_mean_energy_kcal": round(mother_days["energy_sum"] / max(1, mother_days["days"]), 1),
        "nursing_mother_days_below_one_day_reserve": mother_days["below_one_day_reserve"],
        "child_death_contexts": dict(Counter(f'{d["cause"]}|{d["context"]}' for d in child_deaths)),
        "child_deaths": child_deaths,
        "ledger_valid": sim.ledger.verify_chain(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", default=SEEDS[0])
    parser.add_argument("--days", type=int, default=730)
    parser.add_argument("--physiology", default="reference-v1")
    args = parser.parse_args()
    overrides = {} if args.physiology == "reference-v1" else {"agentus_physiology_version": args.physiology}
    print("CAREGIVER_DIAGNOSIS:", json.dumps(run(args.seed, args.days, overrides), sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
