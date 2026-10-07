"""G10.7a step 2: witnessed-event memory changes nothing but itself.

Same seed, memory on and off: every authority's state must be identical once
the memory field (and its bookkeeping counters) are removed.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "experiments" / "genesis"))

from hrm_genesis import GenesisConfig, GenesisSimulation  # noqa: E402
from run_agentus_capacity_multiseed import config_for  # noqa: E402

DAYS = 40
MEMORY_STATS = {"witnessed_events", "witnessed_by_act"}


def _strip(human_state: dict) -> dict:
    state = dict(human_state)
    state.pop("event_memory", None)
    state["capacity_stats"] = {k: v for k, v in state.get("capacity_stats", {}).items() if k not in MEMORY_STATS}
    people = []
    for person in state["humans"]:
        person = dict(person)
        cognition = dict(person["cognition"])
        cognition.pop("witnessed", None)
        person["cognition"] = cognition
        people.append(person)
    state["humans"] = people
    return state


def _run(memory: bool) -> GenesisSimulation:
    config = GenesisConfig(**{**config_for("agentus-demography-a", "v1").__dict__, "agentus_event_memory_enabled": memory})
    sim = GenesisSimulation(config)
    sim.run(DAYS)
    return sim


def test_witnessed_memory_is_recorded_but_changes_no_behaviour():
    on, off = _run(True), _run(False)
    assert on.human_state()["capacity_stats"].get("witnessed_events", 0) > 0, "nothing was witnessed"
    assert any(p["cognition"].get("witnessed") for p in on.human_state()["humans"])
    assert _strip(on.human_state()) == _strip(off.human_state())
    assert on.ecology_state() == off.ecology_state()
    assert on.matter_state() == off.matter_state()
    assert on.consumer_state() == off.consumer_state()
