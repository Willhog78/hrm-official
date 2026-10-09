"""Production-profile, observation-only test of spontaneous material use.
No hunger, water, object or energy injection; uses the viable baseline setup
from the multi-generation runner rather than the harsh 4x4 physiology probe.
"""
from __future__ import annotations
from qualification.genesis.tier_observer import build_config
from hrm_genesis import GenesisConfig, GenesisSimulation
from hrm_genesis.human.interactions import insulation_c

SEEDS=("agentus-demography-a","agentus-demography-b")
DAYS=365

def main():
    for seed in SEEDS:
        base=build_config(seed, "v1")
        config=GenesisConfig(**{**base.__dict__,
            "genesis_wind_enabled":True,
            "agentus_subcell_position_enabled":True})
        sim=GenesisSimulation(config)
        max_alive=0
        previous_wear=0
        for day in range(1,DAYS+1):
            sim.run(1)
            h=sim.human_state()
            st=h.get("capacity_stats",{})
            objs=h.get("objects",[])
            wear_count=int(st.get("worn_surfaces",0))
            if wear_count>previous_wear:
                worn_now=[o for o in objs if o.get("material")=="surface" and o.get("worn")]
                for o in worn_now:
                    owner=next((p for p in h["humans"] if p["id"]==o.get("holder")),None)
                    print(f"WEAR_TRACE seed={seed} day={day} object={o.get('id')} worn={o.get('worn')} holder={o.get('holder')} cohesion={o.get('cohesion')} area={o.get('area_m2')} owner_cold={None if owner is None else owner.get('cold_exposure')} history={o.get('history',[])[-5:]}",flush=True)
                print(f"WEAR_EVENT seed={seed} day={day} attempts_delta={wear_count-previous_wear} worn_now={len(worn_now)} surfaces_state={[(o.get('id'),o.get('holder'),o.get('worn'),o.get('area_m2'),o.get('cohesion')) for o in objs if o.get('material')=='surface']}",flush=True)
                previous_wear=wear_count
            if day in (30,90,180,270,365):
                worn=sum(o.get("worn",False) and o.get("material")=="surface" for o in objs)
                held=sum(o.get("holder") is not None and o.get("material")=="surface" for o in objs)
                alive=len(h["humans"])
                max_alive=max(max_alive,alive)
                print(f"PRODUCTION_DISCOVERY seed={seed} day={day} alive={alive} max_alive={max_alive} "
                      f"surfaces={st.get('surfaces',0)} worn_actions={st.get('worn_surfaces',0)} "
                      f"wear_offers={st.get('wear_affordance_offered',0)} interlace_offers={st.get('interlace_affordance_offered',0)} "
                      f"held_surfaces={held} currently_worn={worn} "
                      f"insulation_saving_kcal={st.get('insulation_saving_kcal',0):.4f} "
                      f"deaths={h.get('cumulative_deaths_by_cause',{})}",flush=True)
        assert sim.ledger.verify_chain()
    print("PRODUCTION_DISCOVERY_COMPLETE",flush=True)

if __name__=="__main__":
    main()
