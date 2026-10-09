"""Costed placement, occupancy and joins use actual material and physiology."""

from copy import deepcopy

import pytest

from _scenario import Scenario, el
from hrm_genesis.human import interactions as cap
from hrm_genesis.human import transitions as tm
from hrm_genesis.human.biology import _apply_physiology, _structural_protection
from hrm_genesis.matter import objects as mo


def scene():
    sc = Scenario(capacities=True)
    sc.humans['local_work_model'] = 'local-material-v1'
    sc.humans['transition_model'] = tm.PROCEDURAL_MODEL
    sc.agent['subcell_offset_m'] = [0.75, 0.5]
    sc.set_agent(0, 0, energy=10000.0)
    profile = dict(sc.profile, development_scale=1.0)
    ctx = cap.Context(sc.humans, sc.agent, profile, sc._p(0, 0), sc.carcass(0, 0),
                      sc.matter['lithic_cells'], sc.world['cells'][0], sc.consumers, 1)
    return sc, ctx


def act(ctx, key):
    spec = dict(cap.enumerate_affordances(ctx))[key]
    out = cap.execute(ctx, key, spec)
    ctx.performed.append((key, out))
    return out


def test_first_placement_tracks_maker_and_additions_do_not_move_existing_material():
    sc, ctx = scene()
    ctx.pcell['loose_material_elements_kg'] = el(0.25)
    before = sum(ctx.pcell['loose_material_elements_kg'].values())
    act(ctx, 'arrange:loose_wood|none')
    geometry = ctx.pcell['arrangement_geometry']
    assert geometry['center_offset_m'] == [0.75, 0.5]
    assert sum(ctx.pcell['arranged_material_elements_kg'].values()) == pytest.approx(before)
    assert geometry['surface_area_m2'] <= before / 15 + 1e-10
    assert _structural_protection({}, ctx.pcell, occupant_offset_m=(0.75, 0.5))[1] > 0
    assert _structural_protection({}, ctx.pcell, occupant_offset_m=(0, 0))[1] == 0
    act(ctx, 'move:local_negative_x|none')
    ctx.pcell['loose_material_elements_kg'] = el(0.25)
    act(ctx, 'arrange:loose_wood|none')
    assert ctx.pcell['arrangement_geometry']['center_offset_m'] == [0.75, 0.5]


def test_local_steps_cost_energy_keep_grid_cell_and_cannot_cross_window():
    sc, ctx = scene()
    xy, energy = ctx.xy, sc.agent['energy']
    out = act(ctx, 'move:local_positive_x|none')
    assert sc.agent['subcell_offset_m'] == [1.0, 0.5]
    assert (sc.agent['x'], sc.agent['y']) == xy
    assert sc.agent['energy'] == pytest.approx(energy - out['effort_kcal'])
    assert out['effort_kcal'] > 0 and sc.agent['fatigue'] > 0
    assert 'move:local_positive_x|none' not in dict(cap.enumerate_affordances(ctx))
    cap.execute(ctx, 'move:local_positive_x|none', {'verb': 'move_local', 'delta': [0.25, 0]})
    assert sc.agent['subcell_offset_m'] == [1.0, 0.5]


def test_distant_arrangement_is_neither_relocated_nor_rotated():
    sc, ctx = scene()
    ctx.pcell['arranged_material_elements_kg'] = el(1)
    ctx.pcell['loose_material_elements_kg'] = el(1)
    ctx.pcell['arrangement_geometry']['center_offset_m'] = [-1, -1]
    before = deepcopy(ctx.pcell)
    assert not any(k.startswith(('arrange:', 'rotate:', 'separate:arranged')) for k, _ in cap.enumerate_affordances(ctx))
    cap.execute(ctx, 'arrange:loose_wood|none', {'verb': 'pool', 'sequence': ('arrange',)})
    cap.execute(ctx, 'rotate:arranged_wood_90|none', {'verb': 'rotate_arrangement', 'angle': 90})
    assert ctx.pcell == before


def test_real_move_into_cover_earns_only_measured_thermal_credit_once():
    sc, ctx = scene()
    sc.agent['subcell_offset_m'] = [0.75, 0]
    ctx.pcell.update(arranged_material_elements_kg=el(30), arrangement_geometry={
        'span_m': 1, 'height_m': 1.2, 'surface_area_m2': 2, 'density': 1})
    ctx = cap.Context(sc.humans, sc.agent, ctx.profile, ctx.pcell, ctx.ccell,
                      ctx.lithic_cells, dict(ctx.wcell, temperature=0), ctx.consumers, 1)
    out = act(ctx, 'move:local_negative_x|none')
    reference, insulation = cap.prepare_thermal_trials(sc.humans, sc.agent, ctx.pcell, 1, ctx.profile, ctx)
    physical_before = deepcopy(sc.agent)
    _apply_physiology(sc.agent, ctx.wcell, 'rest', ctx.profile, ctx.pcell,
                      record_arrangement_benefit=True, arrangement_reference=reference,
                      insulation_reference_c=insulation)
    saving = sc.agent['arrangement_saving_kcal']
    assert saving > 0
    unprotected = deepcopy(physical_before)
    unprotected['subcell_offset_m'] = reference['occupant_offset_m']
    _apply_physiology(unprotected, ctx.wcell, 'rest', ctx.profile, ctx.pcell)
    assert sc.agent['energy'] - unprotected['energy'] == pytest.approx(saving)
    cap.settle_thermal_trials(sc.humans, sc.agent, 1, 0, saving)
    memory = sc.agent['cognition']['transition_memory']
    edge = next(e for e in memory['edges'] if e['id'] == out['transition_edge'])
    gain = edge['gain_sum_basal']
    assert gain == pytest.approx(saving / ctx.profile['basal_energy_kcal_per_tick'])
    cap.settle_thermal_trials(sc.humans, sc.agent, 1, 0, saving)
    assert edge['gain_sum_basal'] == gain
    act(ctx, 'move:local_positive_x|none')
    cap.prepare_thermal_trials(sc.humans, sc.agent, ctx.pcell, 2, ctx.profile)
    assert 'arrangement' not in sc.agent['thermal_trials']


def test_rotation_changes_incident_wind_shielding_and_pays_for_the_same_mass():
    sc, ctx = scene()
    ctx.pcell.update(arranged_material_elements_kg=el(30), arrangement_geometry={
        'span_m': 1.5, 'height_m': 1.2, 'surface_area_m2': 2, 'density': 1,
        'center_offset_m': [0.75, 0.5], 'orientation_deg': 0})
    before = deepcopy(ctx.pcell)
    protected = _structural_protection({}, ctx.pcell, occupant_offset_m=(.75, .5), wind_from_deg=0)[1]
    energy = sc.agent['energy']
    out = act(ctx, 'rotate:arranged_wood_90|none')
    assert out['effort_kcal'] > 0 and sc.agent['energy'] == pytest.approx(energy - out['effort_kcal'])
    assert ctx.pcell['arranged_material_elements_kg'] == before['arranged_material_elements_kg']
    assert ctx.pcell['arrangement_geometry']['center_offset_m'] == [.75, .5]
    assert _structural_protection({}, ctx.pcell, occupant_offset_m=(.75, .5), wind_from_deg=0)[1] < protected


def fiber(ident, **changes):
    result = {'id': ident, 'material': 'fiber', 'source': 'plant', 'elements_kg': el(.001),
              'length_m': 1, 'thickness_mm': 1, 'friction': .6, 'flexibility': .9,
              'integrity': 1, 'moisture_sensitivity': -.2}
    result.update(changes)
    return result


def surfaces():
    return [{'id': f'patch-{i}', 'material': 'surface', 'area_m2': .01, 'cohesion': .9,
             'strands': [fiber(f'{i}-{j}') for j in range(4)]} for i in range(2)]


@pytest.mark.parametrize('changes', [{'length_m': .01}, {'flexibility': .1},
                                    {'friction': .1}, {'integrity': .001}])
def test_bad_seams_fail_without_destroying_material(changes):
    patches, binder = surfaces(), fiber('binder', **changes)
    before = deepcopy((patches, binder))
    assert mo.join_surfaces(patches, binder, 'joined', 0) is None
    assert (patches, binder) == before


def test_live_join_consumes_exact_inputs_preserves_elements_and_existing_decay():
    sc, ctx = scene()
    inputs = surfaces() + [fiber('binder')]
    for obj in inputs:
        obj.update(x=0, y=0, holder=sc.agent['id'], worn=False)
    sc.humans['objects'] = inputs
    before = {}
    for obj in inputs:
        before = mo.merge_elements(before, mo.object_elements(obj))
    out = act(ctx, 'join:surfaces|strand')
    assert out['effort_kcal'] > 0
    joined, = sc.humans['objects']
    assert joined['area_m2'] == pytest.approx(.019)
    assert mo.object_elements(joined) == pytest.approx(before)
    assert len(joined['strands']) == 9
    assert joined['history'][-1] == 'join:surfaces|strand'
    detritus = {}
    cap._degrade(joined, .1, detritus)
    assert mo.merge_elements(mo.object_elements(joined), detritus) == pytest.approx(before)
    assert joined['cohesion'] < .9
    act(ctx, 'wear:surface|held')
    assert cap.insulation_c(sc.humans, sc.agent['id']) > 0


def test_failed_live_join_spends_effort_but_preserves_all_inputs():
    sc, ctx = scene()
    inputs = surfaces() + [fiber('binder', length_m=.01)]
    for obj in inputs:
        obj.update(x=0, y=0, holder=sc.agent['id'], worn=False)
    sc.humans['objects'] = inputs
    before = deepcopy(inputs)
    out = act(ctx, 'join:surfaces|strand')
    assert out['effort_kcal'] > 0
    assert sc.humans['objects'] == before


def test_new_affordances_absent_without_opt_in():
    sc, ctx = scene()
    sc.humans.pop('local_work_model')
    assert not any(k.startswith(('move:local_', 'rotate:', 'join:')) for k, _ in cap.enumerate_affordances(ctx))
