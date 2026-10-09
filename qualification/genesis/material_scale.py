"""Controlled material-response measurements, not autonomous discovery.

No running ecological state, choices or learning are altered. Strands and wood
in these declared fixtures are diagnostic inputs, never gifts to a live agent.
"""

from copy import deepcopy
import argparse
import json
from math import ceil
from pathlib import Path

from hrm_genesis import GenesisSimulation
from hrm_genesis.human import interactions as cap
from hrm_genesis.human.actions import execute_live_sequence
from hrm_genesis.human.biology import _apply_physiology, _structural_protection
from hrm_genesis.matter import objects as mo
from qualification.genesis.discovery import config_for


def strand(source, ident, quantile=.5, length_scale=1.):
    spec = mo.FIBER_SOURCES[source]
    length = mo._span(spec['length_m'], quantile) * length_scale
    thickness = mo._span(spec['thickness_mm'], quantile)
    mass = mo.fiber_mass_for(source, length, thickness)
    return mo.make_fiber(source, {'C': mass}, quantile, quantile, ident, length_scale)


def thermal(body, profile, world, producer=None, insulation=0):
    """One physiology step on two copies; actual debit, not planner reward."""
    bare, covered = deepcopy(body), deepcopy(body)
    bare['subcell_offset_m'] = covered['subcell_offset_m'] = [.5, .5]
    _apply_physiology(bare, world, 'rest', profile, {})
    _apply_physiology(covered, world, 'rest', profile, producer or {}, insulation_c=insulation)
    return {'saving_kcal': covered['energy'] - bare['energy'],
            'bare_thermal_debit_kcal': body['energy'] - bare['energy'],
            'covered_thermal_debit_kcal': body['energy'] - covered['energy'],
            'bare_cold_exposure': bare.get('cold_exposure', 0),
            'covered_cold_exposure': covered.get('cold_exposure', 0)}


def weave_response(body, profile):
    rows = []
    for source in mo.FIBER_SOURCES:
        for count in (4, 6, 24, 100, 300):
            fibers = [strand(source, f'{source}-{i}') for i in range(count)]
            patch = mo.interlace(fibers, f'{source}-patch')
            insulation = cap.insulation_c({'objects': [dict(patch, holder=body['id'], worn=True)]}, str(body['id']))
            row = {'source': source, 'strand_count': count,
                   'fits_live_hand_limit': count <= cap.MAX_SOFT_IN_HAND,
                   'area_m2': patch['area_m2'], 'cohesion': patch['cohesion'],
                   'mass_kg': mo.object_mass(patch), 'insulation_c': insulation,
                   'source_length_m': fibers[0]['length_m'], 'source_thickness_mm': fibers[0]['thickness_mm']}
            row['thermal'] = [dict(temperature_c=t, **thermal(body, profile,
                                 {'temperature': t, 'wind_speed_m_s': 4., 'wind_from_deg': 0.,
                                  'precipitation': 0., 'solar': .5, 'terrain_cover': 0.}, insulation=insulation))
                              for t in (12., -5., -20.)]
            rows.append(row)
    return rows


def join_response():
    """Sequential patch accumulation; no decay, acquisition or work omitted silently."""
    rows = []
    for patch_source in mo.FIBER_SOURCES:
        for binder_source in mo.FIBER_SOURCES:
            patch = mo.interlace([strand(patch_source, f'initial-{i}') for i in range(6)], 'initial')
            initial_mass = mo.object_mass(patch)
            expected_elements = mo.object_elements(patch)
            completed = 0
            cost = 0.
            failure = None
            for attempt in range(1, 65):
                other = mo.interlace([strand(patch_source, f'patch-{attempt}-{i}') for i in range(6)], f'patch-{attempt}')
                binder = strand(binder_source, f'binder-{attempt}')
                cost += 8 + 20 * min(patch['area_m2'], other['area_m2']) ** .5
                result = mo.join_surfaces([patch, other], binder, f'join-{attempt}', 0.)
                if result is None:
                    failure = attempt
                    break
                expected_elements = mo.merge_elements(expected_elements, mo.object_elements(other))
                expected_elements = mo.merge_elements(expected_elements, mo.object_elements(binder))
                patch = result
                completed += 1
            rows.append({'patch_source': patch_source, 'binder_source': binder_source,
                         'completed_joins': completed, 'first_failed_attempt': failure,
                         'search_limit': 64, 'initial_mass_kg': initial_mass,
                         'final_area_m2': patch['area_m2'], 'final_cohesion': patch['cohesion'],
                         'join_effort_kcal_including_failure': cost,
                         'element_abs_error_kg': max(abs(mo.object_elements(patch).get(k, 0) - v)
                                                     for k, v in expected_elements.items())})
    return rows


def twist_response():
    """Existing alternative route: six progressively thicker twisted bundles.

    Work is an optimistic bare-hand adult successful extraction/twist/interlace
    lower bound, using the live hand-extraction length reductions. Ground
    storage, pickups, failures, wear, time, food and travel are excluded.
    """
    rows = []
    for source in mo.FIBER_SOURCES:
        length_scale = {'plant': 1., 'bark': .4, 'tendon': .3}[source]
        bundle = strand(source, f'{source}-raw', length_scale=length_scale)
        for depth in range(11):
            patch = mo.interlace([dict(bundle, id=f'{source}-{depth}-{i}') for i in range(6)], 'bundled-patch')
            raw_count = 6 * 2 ** depth
            extraction_attempts = ceil(raw_count / 3) if source == 'plant' else raw_count
            twist_attempts = 6 * (2 ** depth - 1)
            rows.append({'source': source, 'binary_twist_depth': depth,
                         'raw_strands': raw_count, 'final_held_strands': 6,
                         'area_m2': patch['area_m2'], 'mass_kg': mo.object_mass(patch),
                         'bundle_length_m': bundle['length_m'], 'bundle_thickness_mm': bundle['thickness_mm'],
                         'bundle_integrity': bundle['integrity'],
                         'optimistic_bare_hand_effort_kcal': extraction_attempts * 18 + twist_attempts * 8 + 25,
                         'fits_carry_mass_limit': mo.object_mass(patch) <= cap.CARRY_LIMIT_KG})
            bundle = mo.twist([deepcopy(bundle), deepcopy(bundle)], f'{source}-depth-{depth+1}')
    return rows


def wood_response(body, profile):
    rows = []
    for target in (.25, 1., 5., 15., 30., 60.):
        person = deepcopy(body)
        person['subcell_offset_m'] = [.5, .5]
        cell = {'woody_elements_kg': {'C': 100.}, 'loose_material_elements_kg': {'C': 0.},
                'arranged_material_elements_kg': {'C': 0.}}
        work = 0.
        actions = 0
        # Cost/geometry envelope only: batch loose material before arranging.
        for _ in range(ceil(target / .25)):
            person, cell, trace = execute_live_sequence(('apply_force',), person, cell)
            work += trace['effort_energy_kcal']
            actions += 1
        person, cell, trace = execute_live_sequence(('arrange',), person, cell, placement_offset_m=(.5, .5))
        work += trace['effort_energy_kcal']
        actions += 1
        mass = sum(cell['arranged_material_elements_kg'].values())
        measurements = []
        for temperature in (12., -5., -20.):
            for direction in (0., 90., 180.):
                world = {'temperature': temperature, 'wind_speed_m_s': 4., 'wind_from_deg': direction,
                         'precipitation': 0., 'solar': .5, 'terrain_cover': 0.}
                cover = _structural_protection(world, cell, occupant_offset_m=(.5, .5), wind_from_deg=direction)[1]
                result = thermal(body, profile, world, cell)
                saving = result['saving_kcal']
                measurements.append({'temperature_c': temperature, 'wind_from_deg': direction,
                                     'cover': cover, **result,
                                     'optimistic_payback_days': work / saving if saving > 1e-9 else None})
        rows.append({'arranged_mass_kg': mass, 'geometry': cell['arrangement_geometry'],
                     'effort_kcal': work, 'physical_actions': actions,
                     'minimum_ticks_at_three_actions': ceil(actions / 3),
                     'element_abs_error_kg': abs(sum(sum(cell.get(k, {}).values()) for k in
                                                 ('woody_elements_kg', 'loose_material_elements_kg', 'arranged_material_elements_kg')) - 100.),
                     'measurements': measurements})
    return rows


def measure():
    sim = GenesisSimulation(config_for('agentus-demography-a', True))
    digest_before = sim.ledger.digest()
    snapshot_before = sim.snapshot()
    humans = sim.human_state()
    body = deepcopy(humans['humans'][0])
    profile = deepcopy(humans['physiology_profile'])
    profile['development_scale'] = 1.
    rows = {'controlled_fixtures': True, 'ecological_or_discovery_claim': False,
            'source_config_fingerprint': sim.config.fingerprint(), 'physiology_profile': profile,
            'weave': weave_response(body, profile), 'joins': join_response(),
            'twisted_bundles': twist_response(), 'wood': wood_response(body, profile)}
    rows['source_simulation_unchanged'] = sim.snapshot() == snapshot_before and sim.ledger.digest() == digest_before
    rows['passed'] = (rows['source_simulation_unchanged']
                      and all(r['element_abs_error_kg'] < 1e-9 for r in rows['joins'] + rows['wood']))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = measure()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'passed': result['passed'], 'controlled_fixtures': True}))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
