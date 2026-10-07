"""G10.4: capture requires physical approach and contact."""

from __future__ import annotations

from hrm_genesis.human.interactions import ARM_REACH_M, resolve_encounter


def _enc(**kw):
    base = dict(capability=1.0, fatigue=0.0, reach_m=ARM_REACH_M, strike_energy_j=0.0,
                prey_mass_kg=0.05, prey_perception=1, prey_condition=1.0, draws=[0.5, 0.5, 0.5, 0.5])
    base.update(kw)
    return resolve_encounter(**base)


def test_unnoticed_stalk_reaches_contact_and_costs_walking_distance():
    r = _enc(draws=[0.0, 1e-9, 0.5, 0.0])  # nearest start, very late detection
    assert r["contact"] and r["walked_m"] == 10.0 - ARM_REACH_M and r["sprinted_m"] == 0.0


def test_noticed_healthy_prey_outruns_the_agent():
    r = _enc(prey_perception=2, draws=[0.9, 0.99, 0.5, 0.0])
    assert not r["contact"] and r["outcome"] == "outrun" and r["sprinted_m"] > 0.0


def test_weakened_prey_can_be_run_down():
    r = _enc(prey_condition=0.0, draws=[0.2, 0.95, 0.5, 0.0])
    assert r["contact"]


def test_alert_prey_notices_sooner_than_dull_prey():
    dull = _enc(prey_perception=1, draws=[0.9, 0.3, 0.5, 0.0])
    alert = _enc(prey_perception=3, draws=[0.9, 0.3, 0.5, 0.0])
    assert alert["walked_m"] < dull["walked_m"]


def test_fatigue_makes_the_approach_noticeable():
    fresh = _enc(draws=[0.9, 0.3, 0.5, 0.0])
    tired = _enc(fatigue=1.0, draws=[0.9, 0.3, 0.5, 0.0])
    assert tired["walked_m"] < fresh["walked_m"]


def test_contact_is_required_before_any_kill():
    for i in range(200):
        u = [((i * k * 7919) % 1000) / 1000.0 + 1e-6 for k in (1, 3, 5, 7)]
        r = _enc(draws=u, strike_energy_j=50.0)
        if r["outcome"] == "kill":
            assert r["contact"]


def test_strike_must_carry_enough_energy_and_bare_hands_must_hold():
    weak = _enc(draws=[0.0, 1e-9, 0.0, 0.99], strike_energy_j=0.5)
    strong = _enc(draws=[0.0, 1e-9, 0.0, 0.99], strike_energy_j=50.0)
    assert weak["outcome"] == "contact_failed" and strong["outcome"] == "kill"
    slips = _enc(draws=[0.0, 1e-9, 0.5, 0.99])
    holds = _enc(draws=[0.0, 1e-9, 0.5, 0.01])
    assert slips["outcome"] == "contact_failed" and holds["outcome"] == "kill"


def test_longer_reach_shortens_the_approach():
    short = _enc(draws=[0.5, 1e-9, 0.5, 0.0])
    long = _enc(reach_m=ARM_REACH_M + 1.5, draws=[0.5, 1e-9, 0.5, 0.0])
    assert long["walked_m"] < short["walked_m"]
