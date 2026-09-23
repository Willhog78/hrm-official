from hrm_sandbox import Sim
from hrm_sandbox.humans import KNOW


def _fingerprint(sim: Sim):
    return [(s["t"], s["pop"], s["rabbits"], s["berries"], s["nuts"], tuple(sorted(s["known"].items())))
            for s in sim.observer.series]


def test_same_seed_same_history():
    a, b = Sim(seed=11), Sim(seed=11)
    a.run(400)
    b.run(400)
    assert _fingerprint(a) == _fingerprint(b)


def test_different_seeds_diverge():
    a, b = Sim(seed=11), Sim(seed=12)
    a.run(300)
    b.run(300)
    assert _fingerprint(a) != _fingerprint(b)


def test_nobody_starts_with_techniques():
    sim = Sim(seed=3)
    assert all(not h.q and not h.known for h in sim.humans)
    assert sim.observer.series[0]["known"] == {}


def test_every_known_behaviour_has_a_recorded_source():
    sim = Sim(seed=2)
    sim.run(800)
    for h in sim.humans:
        for key, (tick, source) in h.known.items():
            assert key[0] != "hand"
            assert 0 < tick <= sim.tick
            assert source == h.id or source in sim.by_id
    for ev in sim.observer.events:
        assert ev["how"] in ("discovered", "learned by watching")


def test_learning_is_reversible():
    """A behaviour that stops paying drops back below the 'known' level."""
    sim = Sim(seed=1)
    h = sim.humans[0]
    key = ("H--", "strike", "nut")
    for _ in range(10):
        h.learn(key, 14.0, None, 0.25, 1, h.id)
    assert h.q[key] >= KNOW
    for _ in range(20):
        h.learn(key, 0.0, None, 0.25, 2, h.id)
    assert h.q[key] < KNOW
