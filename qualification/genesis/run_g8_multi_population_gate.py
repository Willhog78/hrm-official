from __future__ import annotations

from collections import defaultdict

from hrm_genesis import GenesisConfig, GenesisSimulation
from hrm_genesis.human.perception import perceive_local
from hrm_genesis.human.regions import POPULATION_IDS, population_counts, resource_profile


def _cross_population_contacts(humans: list[dict]) -> list[tuple[str, str]]:
    contacts = []
    for i, a in enumerate(humans):
        for b in humans[i + 1:]:
            if a.get("population_id") == b.get("population_id"):
                continue
            distance = abs(int(a["x"]) - int(b["x"])) + abs(int(a["y"]) - int(b["y"]))
            if distance <= 1:
                contacts.append((str(a["id"]), str(b["id"])))
    return contacts


def _preferred_cells(humans: list[dict]) -> dict[str, tuple[int, int] | None]:
    by_population: dict[str, list[tuple[float, str]]] = defaultdict(list)
    for human in humans:
        pid = str(human.get("population_id"))
        cognition = human.get("cognition", {})
        for key, value in cognition.get("expectations", {}).items():
            by_population[pid].append((float(value), str(key)))

    preferred: dict[str, tuple[int, int] | None] = {}
    for pid in POPULATION_IDS:
        rows = by_population.get(pid, [])
        if not rows:
            preferred[pid] = None
            continue
        _, key = max(rows, key=lambda row: (row[0], row[1]))
        x, y = key.split(",")
        preferred[pid] = (int(x), int(y))
    return preferred


def main() -> int:
    config = GenesisConfig(
        master_seed="genesis-g8-multi-population",
        world_width=8,
        world_height=8,
        ticks_per_year=12,
        producer_ecology_enabled=True,
        consumer_ecology_enabled=True,
        human_biology_enabled=True,
        human_cognition_enabled=True,
        human_actions_enabled=True,
        multi_population_enabled=True,
    )

    sim = GenesisSimulation(config)
    initial_humans = sim.human_state()["humans"]
    initial_counts = population_counts(sim.human_state())
    initial_contacts = _cross_population_contacts(initial_humans)
    profiles = {
        pid: resource_profile(pid, sim.ecology_state(), sim.matter_state())
        for pid in POPULATION_IDS
    }

    initial_positions = {str(h["id"]): (int(h["x"]), int(h["y"])) for h in initial_humans}
    sim.run(1)
    after_one = sim.human_state()["humans"]
    max_step = 0
    for human in after_one:
        hid = str(human["id"])
        if hid not in initial_positions:
            continue
        ox, oy = initial_positions[hid]
        step = abs(int(human["x"]) - ox) + abs(int(human["y"]) - oy)
        max_step = max(max_step, step)

    sim.run(35)
    final_humans = sim.human_state()["humans"]
    final_counts = population_counts(sim.human_state())
    preferred = _preferred_cells(final_humans)

    # Prove region boundaries are not causal walls: local perception can see
    # across the midpoint boundary if an agent actually reaches it.
    probe = dict(final_humans[0]) if final_humans else {"id": "probe"}
    probe["x"], probe["y"] = 3, 1
    perceived = perceive_local(probe, sim.ecology_state(), sim.matter_state(), [])
    sees_across_boundary = any(
        int(cell["x"]) == 4 and int(cell["y"]) == 1
        for cell in perceived["cells"]
    )

    profile_signatures = {
        (
            round(v["mean_food_kg"], 8),
            round(v["mean_water_kg"], 8),
            round(v["max_food_kg"], 8),
            round(v["max_water_kg"], 8),
        )
        for v in profiles.values()
    }
    preferred_values = [v for v in preferred.values() if v is not None]

    checks = {
        "four_founder_populations": set(initial_counts) == set(POPULATION_IDS),
        "two_founders_per_population": all(initial_counts.get(pid, 0) == 2 for pid in POPULATION_IDS),
        "initial_separation": len(initial_contacts) == 0,
        "heterogeneous_resource_regions": len(profile_signatures) >= 2,
        "travel_is_local": max_step <= 1,
        "cross_region_contact_possible": sees_across_boundary,
        "all_populations_gain_history": all(preferred.get(pid) is not None for pid in POPULATION_IDS),
        "histories_diverge": len(set(preferred_values)) >= 2,
        "population_origin_retained": all(
            "population_id" in human and "home_region" in human
            for human in final_humans
        ),
        "no_scripted_social_state": all(
            not any(
                key in human
                for key in (
                    "nation", "government", "religion", "profession",
                    "culture", "faction", "technology", "war", "trade_policy",
                )
            )
            for human in final_humans
        ),
        "ledger_valid": sim.ledger.verify_chain(),
    }

    for name, passed in checks.items():
        print(f"{name}: {'PASS' if passed else 'FAIL'}")

    print("G8_INITIAL_COUNTS:", initial_counts)
    print("G8_FINAL_COUNTS:", final_counts)
    print("G8_RESOURCE_PROFILES:", profiles)
    print("G8_PREFERRED_CELLS:", preferred)

    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        print("G8_GATE_FAIL:", ", ".join(failed))
        return 1

    print("G8_GATE_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
