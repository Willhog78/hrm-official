"""The opportunity census must observe without causing, and must classify the
planner's situation in the planner's own order."""

from __future__ import annotations

from qualification.genesis.opportunity import Census, classify, run_census
from qualification.genesis.tier_observer import unobserved_digest
import hrm_genesis.human.biology as biology
import hrm_genesis.human.interactions as cap


def _perception(own_food: float, neighbour_food: float, need: float = 1.0, reserve: float = 0.5,
                remembered: list | None = None, peers: list | None = None) -> dict:
    cells = [
        {"x": 1, "y": 1, "food_kg": own_food, "water_kg": 100.0},
        {"x": 2, "y": 1, "food_kg": neighbour_food, "water_kg": 100.0},
    ]
    p = {"origin": [1, 1], "cells": cells, "forage_need_kg": need, "energy_reserve_fraction": reserve,
         "partial_food_anchor": True}
    if remembered is not None:
        p["remembered_food"] = remembered
    if peers is not None:
        p["visible_peers"] = peers
    return p


def test_classify_follows_planner_order():
    assert classify(_perception(2.0, 0.0), {})["food"] == "full_in_view"
    assert classify(_perception(0.0, 0.0, remembered=[[5, 5, 3.0, 0]]), {})["food"] == "full_remembered"
    # A remembered place that would not cover the need does not count.
    assert classify(_perception(0.3, 0.0, remembered=[[5, 5, 0.5, 0]]), {})["food"] == "partial_in_view"
    assert classify(_perception(0.1, 0.0), {})["food"] == "none"


def test_classify_hunger_and_peers():
    r = classify(_perception(0.0, 0.0, reserve=0.9, peers=[("b", 2, 1)]), {})
    assert not r["H"] and r["P"] and not r["C"]
    r = classify(_perception(0.0, 0.0, reserve=0.5, peers=[("b", 1, 1)]), {})
    assert r["H"] and r["P"] and r["C"]
    r = classify(_perception(0.0, 0.0), {})
    assert not r["P"] and not r["peers_tracked"]


def test_census_uninstalls_cleanly():
    originals = (biology.choose_destination, cap.remember_witnessed, cap.observe_outcome)
    census = Census()
    census.install()
    assert biology.choose_destination is not originals[0]
    census.uninstall()
    assert (biology.choose_destination, cap.remember_witnessed, cap.observe_outcome) == originals


def test_census_is_non_causal():
    seed, arm, days = "agentus-demography-a", "v1", 12
    result = run_census(seed, arm, days)
    assert "crash" not in result, result.get("traceback")
    assert result["ledger_valid"]
    assert result["peers_tracked"]
    assert result["buckets"]["all"]["agent_days"] > 0
    assert result["ledger_digest"] == unobserved_digest(seed, arm, days)
