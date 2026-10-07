"""G10.3 capacity model v1: multiseed comparison with ablations.

Arms (same seeds, same world, same resource quantities):
  v0               capacities off (the pre-G10.3 model on the current main)
  v1               capacity model v1
  plant_diet       v1 without sampling unknown food kinds
  no_interactions  v1 without manipulation or capture
  no_recall        v1 without travel toward remembered food

Every measurement below is read after a tick; nothing here feeds back into the
simulation. Results print as JSON lines (usable from a log) and optionally
write to --out.

Usage:
  python experiments/genesis/run_agentus_capacity_multiseed.py --arm v1 --seed agentus-demography-a
"""

from __future__ import annotations

import argparse
import json
from collections import Counter

from hrm_genesis import GenesisConfig, GenesisSimulation
from hrm_genesis.human.interactions import lithic_inventory_kg


SEEDS = [
    "agentus-demography-a",
    "agentus-demography-b",
    "agentus-demography-c",
    "agentus-demography-d",
]
DAYS = 730
ARMS = ("v0", "v1", "plant_diet", "no_interactions", "no_recall")


def config_for(seed: str, arm: str) -> GenesisConfig:
    return GenesisConfig(
        master_seed=seed,
        world_width=16,
        world_height=16,
        ticks_per_year=365,
        producer_ecology_enabled=True,
        consumer_ecology_enabled=True,
        human_biology_enabled=True,
        human_cognition_enabled=True,
        human_actions_enabled=True,
        multi_population_enabled=True,
        material_scale_factor=1000.0,
        human_calibration_enabled=True,
        agentus_capacities_enabled=arm != "v0",
        agentus_capacity_ablation="" if arm in {"v0", "v1"} else arm,
    )


def _mass(elements: dict) -> float:
    return sum(float(v) for v in elements.values())


def availability(sim: GenesisSimulation) -> dict[str, float]:
    producers = sim.ecology_state()["cells"]
    carcasses = sim.consumer_state()["carcass_cells"]
    return {
        "plant_tissue_kg": sum(_mass(c["plant_elements_kg"]) for c in producers),
        "seed_kg": sum(_mass(c["seed_elements_kg"]) for c in producers),
        "woody_kg": sum(_mass(c.get("woody_elements_kg", {})) for c in producers),
        "fresh_tissue_kg": sum(_mass(c.get("fresh_elements_kg", {})) for c in carcasses),
        "animal_body_kg": sum(_mass(a["body_elements_kg"]) for a in sim.consumer_state()["animals"]),
        "animals": len(sim.consumer_state()["animals"]),
    }


def run(seed: str, arm: str, days: int) -> dict:
    sim = GenesisSimulation(config_for(seed, arm))
    daily = []
    adult_deaths_before_300 = 0
    seen_dead: set[str] = set()
    for day in range(days):
        sim.run(1)
        humans = sim.human_state()
        if day % 7 == 0 or day == days - 1:
            daily.append({"day": day + 1, "agentus": len(humans["humans"]), **availability(sim)})
        profile = humans["physiology_profile"]
        for record in humans.get("death_records", []):
            if record["id"] in seen_dead:
                continue
            seen_dead.add(record["id"])
            if day < 300 and int(record.get("generation", 0)) == 0:
                adult_deaths_before_300 += 1

    humans = sim.human_state()
    consumers = sim.consumer_state()
    people = humans["humans"]
    maturity = int(humans["physiology_profile"]["maturity_ticks"])
    by_population: dict[str, dict[str, int]] = {}
    for person in people:
        bucket = by_population.setdefault(str(person.get("population_id")), Counter())
        bucket[str(person["sex"])] += 1
        if int(person["age_ticks"]) >= maturity:
            bucket[f"adult_{person['sex']}"] += 1

    learned_positive: Counter = Counter()
    food_known: Counter = Counter()
    for person in people:
        cognition = person.get("cognition", {})
        for key, entry in cognition.get("affordance_values", {}).items():
            if float(entry["v"]) > 0.0:
                learned_positive[key] += 1
        for kind, value in cognition.get("food_values", {}).items():
            if float(value) > 0.0:
                food_known[kind] += 1

    stats = humans.get("capacity_stats", {})
    lithic = None
    if "initial_lithic_kg" in sim.matter_state():
        lithic = lithic_inventory_kg(sim.matter_state(), humans) - float(sim.matter_state()["initial_lithic_kg"])

    def summary(key: str) -> dict:
        values = [d[key] for d in daily]
        return {"min": min(values), "mean": sum(values) / len(values), "final": values[-1]}

    return {
        "seed": seed,
        "arm": arm,
        "days": days,
        "config_fingerprint": sim.config.fingerprint(),
        "agentus_final": len(people),
        "adults_final": sum(1 for p in people if int(p["age_ticks"]) >= maturity),
        "births": int(humans.get("cumulative_births", 0)),
        "deaths": int(humans.get("cumulative_deaths", 0)),
        "deaths_by_cause": humans.get("cumulative_deaths_by_cause", {}),
        "founder_deaths_before_day_300": adult_deaths_before_300,
        "by_population": {k: dict(v) for k, v in sorted(by_population.items())},
        "breeding_pairs_final": sum(1 for v in by_population.values() if v.get("adult_female") and v.get("adult_male")),
        "availability": {k: summary(k) for k in ("plant_tissue_kg", "seed_kg", "woody_kg", "fresh_tissue_kg", "animal_body_kg", "animals")},
        "intake_kg_by_kind": stats.get("intake_kg_by_kind", {}),
        "intake_kcal_by_kind": stats.get("intake_kcal_by_kind", {}),
        "ingestion_hazard": stats.get("ingestion_hazard", 0.0),
        "interaction_counts": stats.get("interaction_counts", {}),
        "interaction_effort_kcal": stats.get("interaction_effort_kcal", 0.0),
        "interaction_injury": stats.get("interaction_injury", 0.0),
        "material_events": {k: stats.get(k, 0) for k in (
            "capture_attempts", "captures", "capture_escapes", "fractures", "sharp_flakes",
            "fibers_extracted", "wood_pieces", "bindings", "binding_failures",
            "binding_load_slips", "binding_load_breaks", "surfaces", "worn_surfaces",
        )},
        "animal_deaths_by_cause": consumers.get("cumulative_deaths_by_cause", {}),
        "living_agentus_with_positive_learned_interactions": dict(learned_positive.most_common(12)),
        "living_agentus_food_kinds_valued": dict(food_known),
        "objects_in_world": len(humans.get("objects", [])),
        "lithic_ledger_error_kg": lithic,
        "ledger_valid": sim.ledger.verify_chain(),
        "weekly_series": daily,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--arm", choices=ARMS, required=True)
    parser.add_argument("--seed", choices=SEEDS + ["all"], default="all")
    parser.add_argument("--days", type=int, default=DAYS)
    parser.add_argument("--out")
    args = parser.parse_args()
    seeds = SEEDS if args.seed == "all" else [args.seed]
    results = []
    for seed in seeds:
        result = run(seed, args.arm, args.days)
        results.append(result)
        compact = {k: v for k, v in result.items() if k != "weekly_series"}
        print("CAPACITY_RESULT:", json.dumps(compact, sort_keys=True), flush=True)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            json.dump(results, handle, sort_keys=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
