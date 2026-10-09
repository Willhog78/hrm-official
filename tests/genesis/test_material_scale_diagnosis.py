"""Response probes must stay non-causal and distinguish bounds from live acts."""

import pytest

from qualification.genesis.material_scale import measure


@pytest.fixture(scope='module')
def result():
    return measure()


def test_controlled_probe_is_reproducible_and_leaves_source_world_unchanged(result):
    assert result == measure()
    assert result['passed'] and result['source_simulation_unchanged']
    assert result['controlled_fixtures'] and not result['ecological_or_discovery_claim']
    assert max(r['element_abs_error_kg'] for r in result['joins'] + result['wood']) < 1e-9


def test_larger_low_level_weaves_are_distinguished_from_current_hand_capacity(result):
    plant = {r['strand_count']: r for r in result['weave'] if r['source'] == 'plant'}
    assert plant[6]['fits_live_hand_limit']
    assert not plant[100]['fits_live_hand_limit']
    assert plant[100]['area_m2'] > plant[6]['area_m2']
    assert any(r['area_m2'] > plant[6]['area_m2'] for r in result['twisted_bundles'] if r['source'] == 'plant')


def test_seam_limits_and_weather_savings_do_not_become_discovery_claims(result):
    joins = {(r['patch_source'], r['binder_source']): r for r in result['joins']}
    assert joins['plant', 'plant']['first_failed_attempt'] == 3
    assert joins['plant', 'bark']['completed_joins'] == joins['plant', 'bark']['search_limit']
    wood = next(r for r in result['wood'] if r['arranged_mass_kg'] == 30)
    front = next(m for m in wood['measurements'] if m['temperature_c'] == -5 and m['wind_from_deg'] == 0)
    back = next(m for m in wood['measurements'] if m['temperature_c'] == -5 and m['wind_from_deg'] == 180)
    assert front['saving_kcal'] > back['saving_kcal'] == 0
    assert front['optimistic_payback_days'] > 0
    assert wood['minimum_ticks_at_three_actions'] >= 41
