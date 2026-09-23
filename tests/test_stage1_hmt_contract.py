"""Thin rerun hooks for the locked HMT Stage-1 card implementations.

The scored Gate run is qualification/hmt_stage1_gate.py with the locked activation
manifest. These pytest hooks make each card independently reproducible by reviewers.
"""
from qualification.hmt_stage1_gate import CARDS


def _make_test(card_id, fn):
    def test():
        result = fn()
        assert result.get("pass") is True, result
    test.__name__ = "test_" + card_id.lower().replace("-", "_")
    return test


for _card_id, _fn in CARDS:
    globals()["test_" + _card_id.lower().replace("-", "_")] = _make_test(_card_id, _fn)
