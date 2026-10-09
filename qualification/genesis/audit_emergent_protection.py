"""Observable, non-scripted Agentus material discovery and protection usage."""
from hrm_genesis import GenesisConfig, GenesisSimulation

def main():
    for seed in ("exposure-a", "exposure-b", "exposure-c", "exposure-d"):
        cfg = GenesisConfig(
            master_seed=seed, world_width=4, world_height=4,
            ticks_per_year=365, material_scale_factor=1000.0,
            producer_ecology_enabled=True, consumer_ecology_enabled=True,
            human_biology_enabled=True, human_cognition_enabled=True,
            human_actions_enabled=True, human_calibration_enabled=True,
            agentus_capacities_enabled=True, genesis_wind_enabled=True,
            agentus_subcell_position_enabled=True,
        )
        sim = GenesisSimulation(cfg)
        made = worn = savings = max_objects = offers_wear = offers_interlace = 0
        surfaces_held = 0
        for day in range(1, 91):
            sim.run(1)
            h = sim.human_state()
            stats = h.get("capacity_stats", {})
            objs = h.get("objects", [])
            made = max(made, int(stats.get("surfaces", 0)))
            worn = max(worn, int(stats.get("worn_surfaces", 0)))
            savings = max(savings, float(stats.get("insulation_saving_kcal", 0.0)))
            max_objects = max(max_objects, len(objs))
            offers_wear = max(offers_wear, int(stats.get("wear_affordance_offered", 0)))
            offers_interlace = max(offers_interlace, int(stats.get("interlace_affordance_offered", 0)))
            surfaces_held = max(surfaces_held, sum(o.get("material") == "surface" and o.get("holder") is not None for o in objs))
        h = sim.human_state()
        stats = h.get("capacity_stats", {})
        counts = stats.get("interaction_counts", {})
        relevant = {k:v for k,v in counts.items() if any(token in k for token in ("interlace", "wear:", "arrange:", "separate:", "grasp:"))}
        print(f"DISCOVERY seed={seed} alive={len(h['humans'])} surfaces={made} worn_actions={worn} "
              f"insulation_saving_kcal={savings:.6f} max_objects={max_objects} "
              f"wear_offers={offers_wear} interlace_offers={offers_interlace} held_surfaces={surfaces_held} "
              f"relevant_actions={relevant}", flush=True)
        assert sim.ledger.verify_chain()
    print("DISCOVERY_AUDIT_COMPLETE", flush=True)

if __name__ == "__main__":
    main()
