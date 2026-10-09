"""A physically handled new surface is not automatically worn; repeated chance
encounters can lead to contact, then actual thermal savings reinforce its history."""
from copy import deepcopy
from hrm_genesis.human import interactions as cap
from hrm_genesis.human.biology import _apply_physiology

def test_repeat_encounter_and_experienced_heat_saving():
    human = {"id":"h", "x":0, "y":0, "energy":10000.0,
        "body_water_kg":42.0,"fatigue":0.0,"injury":0.0,
        "core_temperature_c":37.0,
        "cognition":{"affordance_values":{}, "trace":[]}}
    surface={"id":"s","material":"surface","holder":"h","x":0,"y":0,
             "worn":False,"area_m2":1.8,"cohesion":0.9,
             "first_handled_epoch":10,"history":["interlace:strands|held"]}
    humans={"objects":[surface],"capacity_stats":cap.empty_stats()}
    profile={"calibrated":True,"thermal_scale":1.0,"water_capacity_kg":42.0,
             "basal_energy_kcal_per_tick":100.0}
    world={"temperature":-15.0, "precipitation":0.0,"solar":0.0,
           "wind_speed_m_s":4.0,"wind_from_deg":0.0}
    ctx=cap.Context(humans,human,profile,{},None,{},world,{},10)
    options=[("wear:surface|held",{"verb":"wear","id":"s"})]
    # First demonstrate that a novel, reachable surface is merely available,
    # rather than mandatory; an adverse draw leaves it unused.
    ctx.draw=lambda key,step: 0.99
    assert cap.choose(ctx,options,0,False) is None
    assert not surface["worn"]
    # An independently favorable general exploration draw tries the contact.
    ctx.draw=lambda key,step: 0.0
    selected=cap.choose(ctx,options,1,False)
    assert selected==options[0]
    cap.execute(ctx,*selected)
    assert surface["worn"]
    assert cap.insulation_c(humans,"h")>0
    # No arbitrary reward injection: physiological model calculates actual
    # reduction in cold-energy expenditure compared with a bare body.
    _apply_physiology(human,world,False,profile,{},
                      insulation_c=cap.insulation_c(humans,"h"))
    saved=float(human.pop("insulation_saving_kcal",0))
    assert saved>0
    cap.credit_worn_benefit(humans,human,saved,profile)
    values=human["cognition"]["affordance_values"]
    assert values["wear:surface|held"]["v"]>0
    assert values["interlace:strands|held"]["v"]>0 if "interlace:strands|held" in values else True
    assert humans["capacity_stats"]["insulation_saving_kcal"]>0
