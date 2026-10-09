"""Novelty influences exploration for any newly handled object, not clothing specifically."""
from hrm_genesis.human import interactions as cap

class Dummy:
    def __init__(self, weather, obj):
        self.wcell = {"wind_speed_m_s": 2.0} if weather else {}
        self.epoch = 10
        self.agent_id = "h"
        self.human = {"cognition": {"affordance_values": {}}}
        self.humans = {"objects": [obj]}
        self.stats = {}
    def draw(self, key, step):
        return 0.20 if key == "explore" else 0.999

def test_novelty_applies_to_generic_stone():
    obj = {"id": "s", "material": "stone", "holder": "h", "first_handled_epoch": 10}
    ctx = Dummy(True, obj)
    picked = cap.choose(ctx, [("inspect:stone|held", {"verb": "inspect", "id": "s"})], 0, False)
    assert picked is not None

def test_legacy_exploration_probability_unchanged():
    obj = {"id": "s", "material": "stone", "holder": "h", "first_handled_epoch": 10}
    ctx = Dummy(False, obj)
    assert cap.choose(ctx, [("inspect:stone|held", {"verb": "inspect", "id": "s"})], 0, False) is None

def test_old_object_no_novelty():
    obj = {"id": "s", "material": "stone", "holder": "h", "first_handled_epoch": 1}
    ctx = Dummy(True, obj)
    assert cap.choose(ctx, [("inspect:stone|held", {"verb": "inspect", "id": "s"})], 0, False) is None
