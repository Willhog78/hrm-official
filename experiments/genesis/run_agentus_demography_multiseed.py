from __future__ import annotations

import json

from hrm_genesis import GenesisConfig, GenesisSimulation


SEEDS = [
    "agentus-demography-a",
    "agentus-demography-b",
    "agentus-demography-c",
    "agentus-demography-d",
]
DAYS = 730


def summarize(sim: GenesisSimulation, seed: str) -> dict:
    humans = sim.human_state()
    people = list(humans["humans"])
    by_population = {}
    reproductive_populations = 0
    for person in people:
        pid = str(person.get("population_id", "unassigned"))
        bucket = by_population.setdefault(pid, {"female": 0, "male": 0, "total": 0})
        bucket[str(person["sex"])] += 1
        bucket["total"] += 1
    for bucket in by_population.values():
        if bucket["female"] > 0 and bucket["male"] > 0:
            reproductive_populations += 1

    return {
        "seed": seed,
        "days": DAYS,
        "agentus": len(people),
        "births": int(humans.get("cumulative_births", 0)),
        "deaths": int(humans.get("cumulative_deaths", 0)),
        "by_population_and_sex": by_population,
        "reproductive_populations": reproductive_populations,
        "extinct": len(people) == 0,
        "ledger_valid": sim.ledger.verify_chain(),
    }


def main() -> int:
    results = []
    for seed in SEEDS:
        config = GenesisConfig(
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
        )
        sim = GenesisSimulation(config)
        sim.run(DAYS)
        result = summarize(sim, seed)
        results.append(result)
        print("DEMOGRAPHY_SEED:", json.dumps(result, sort_keys=True), flush=True)

    print("DEMOGRAPHY_SUMMARY:", json.dumps({
        "seeds": len(results),
        "extinct_by_two_years": sum(1 for r in results if r["extinct"]),
        "zero_reproductive_populations": sum(1 for r in results if r["reproductive_populations"] == 0),
        "mean_agentus": sum(r["agentus"] for r in results) / len(results),
        "total_births": sum(r["births"] for r in results),
        "all_ledgers_valid": all(r["ledger_valid"] for r in results),
    }, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
