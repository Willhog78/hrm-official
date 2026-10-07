"""The tier observer must notice the violations it claims to check."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "micro"))

from _scenario import Scenario  # noqa: E402
from hrm_genesis.human import interactions as cap  # noqa: E402
from qualification.genesis.tier_observer import Observer, evaluate  # noqa: E402


def _ctx(sc: Scenario) -> cap.Context:
    xy = sc.xy
    pcell = next(c for c in sc.producers["cells"] if (c["x"], c["y"]) == xy)
    return cap.Context(sc.humans, sc.agent, dict(sc.profile, development_scale=1.0), pcell, sc.carcass(*xy),
                       sc.matter["lithic_cells"], {"precipitation": 0.0}, sc.consumers, 3)


def test_observer_flags_remote_capture_pickup_and_tool():
    sc = Scenario(capacities=True)
    sc.add_animal("grazer-far", "grazer", 3, 0)
    sc.add_stone(2, 0, "far-stone")
    sc.humans["objects"].append({"id": "lying", "material": "stone", "x": 4, "y": 0, "holder": None, "worn": False,
                                 "fragment": {"id": "lying", "lith": "basaltic", "m": 0.5, "s": 0.1, "e": 1.0}})
    obs = Observer()
    ctx = _ctx(sc)
    obs._check_access(ctx, "strike:animal_grazer|none", {"verb": "capture", "tool": None, "animal": "grazer-far"})
    obs._check_access(ctx, "grasp:stone_heavy|none", {"verb": "grasp_natural", "id": "far-stone"})
    obs._check_access(ctx, "grasp:stone_heavy|none", {"verb": "grasp_object", "id": "lying"})
    obs._check_access(ctx, "cut:fresh_tissue|stone_heavy", {"verb": "cut_tissue", "tool": "lying"})
    assert obs.c["FAIL_remote_capture"] == 1
    assert obs.c["FAIL_remote_pickup"] == 2
    assert obs.c["FAIL_remote_tool"] == 1


def test_observer_accepts_local_access():
    sc = Scenario(capacities=True)
    sc.add_animal("grazer-here", "grazer", 0, 0)
    sc.add_stone(0, 0, "here-stone")
    obs = Observer()
    ctx = _ctx(sc)
    obs._check_access(ctx, "strike:animal_grazer|none", {"verb": "capture", "tool": None, "animal": "grazer-here"})
    obs._check_access(ctx, "grasp:stone_heavy|none", {"verb": "grasp_natural", "id": "here-stone"})
    assert not any(k.startswith("FAIL_") for k in obs.c)


def test_evaluate_turns_broken_invariants_into_failures():
    run = {
        "ledger_valid": False, "numeric": {"non_finite": 2},
        "conservation": {"element_rel_error": 1e-3, "water_rel_error": 0.0, "lithic_abs_error_kg": None},
        "observer": {"FAIL_duplicate_kill": 1, "interactions": 10, "exploited_noops": 1},
        "max_interactions_per_agent_day": 9, "hunting": {"captures": 0},
        "max_noop_habit_repeats": 12, "noop_habits": {"a|k": 12},
        "death_context": {"dehydration|adult|water_visible": 1}, "founders": 8, "alive_min": 8,
        "fatigue_blocked_share": 0.0,
    }
    fails = " ".join(evaluate(run)["fail"])
    for needle in ("ledger", "non_finite", "element balance", "duplicate_kill", "budget", "superstition", "water-seeking"):
        assert needle in fails, needle
