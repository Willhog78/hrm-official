"""Read-only audit: autonomous arranged cover and worn materials in one run.

No shelters are seeded, no actions are selected for Agentus, and no changes
are made to simulation state beyond ordinary time advancement.
"""
from hrm_genesis import GenesisConfig, GenesisSimulation
from qualification.genesis.tier_observer import build_config

SEEDS = ("agentus-demography-a", "agentus-demography-b")
DAYS = 365


def _mass(elements):
    return sum(float(v) for v in elements.values())


def main():
    for seed in SEEDS:
        base = build_config(seed, "v1")
        config = GenesisConfig(**{
            **base.__dict__,
            "genesis_wind_enabled": True,
            "agentus_subcell_position_enabled": True,
        })
        sim = GenesisSimulation(config)
        max_arrangement_mass = 0.0
        occupied_cover_days = 0
        worn_days = 0
        exposed_days = 0
        initial_arrangement = None
        for day in range(1, DAYS + 1):
            sim.run(1)
            humans = sim.human_state()
            producers = sim.producer_state()
            # Producer representation may differ by configuration: this
            # audit must fail visibly rather than fabricate a zero baseline.
            if not isinstance(producers, dict):
                raise TypeError("Unexpected producer state layout")
            cells = producers.get("cells")
            if not isinstance(cells, list):
                raise ValueError("Producer cells unavailable: audit needs adapter")
            arranged = {
                (int(c["x"]), int(c["y"])): c
                for c in cells
                if _mass(c.get("arranged_material_elements_kg", {})) > 0
            }
            amount = sum(_mass(c["arranged_material_elements_kg"]) for c in arranged.values())
            if initial_arrangement is None:
                initial_arrangement = amount
            max_arrangement_mass = max(max_arrangement_mass, amount)
            worn_owners = {
                obj.get("holder") for obj in humans.get("objects", [])
                if obj.get("material") == "surface" and obj.get("worn")
            }
            for person in humans["humans"]:
                position = (int(person["x"]), int(person["y"]))
                if position in arranged:
                    occupied_cover_days += 1
                else:
                    exposed_days += 1
                if person["id"] in worn_owners:
                    worn_days += 1
            if day in (1, 90, 180, 270, 365):
                print(f"JOINT_PROTECTION seed={seed} day={day} "
                      f"arrangement_mass_kg={amount:.8f} "
                      f"arrangement_cells={len(arranged)} "
                      f"covered_occupant_days={occupied_cover_days} "
                      f"worn_occupant_days={worn_days} "
                      f"outside_arrangement_days={exposed_days}", flush=True)
        assert sim.ledger.verify_chain()
        print(f"JOINT_PROTECTION_FINAL seed={seed} "
              f"first_observed_arrangement_mass_kg={initial_arrangement:.8f} "
              f"peak_arrangement_mass_kg={max_arrangement_mass:.8f} "
              f"covered_occupant_days={occupied_cover_days} "
              f"worn_occupant_days={worn_days}", flush=True)
    print("JOINT_PROTECTION_AUDIT_COMPLETE", flush=True)


if __name__ == "__main__":
    main()
