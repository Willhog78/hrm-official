from copy import deepcopy

from hrm_genesis.observer import observe_genesis


def test_observer_is_pure_over_snapshot_data():
    world = {"cells": [{"temperature": 20.0}]}
    matter = {"cells": [{"surface_water_kg": 1.0, "soil_water_kg": 2.0}]}
    producers = {"cells": [{"plant_elements_kg": {"C": 0.5}}]}
    consumers = {"consumers": []}
    humans = {"humans": []}

    original = deepcopy((world, matter, producers, consumers, humans))

    report = observe_genesis(
        world_state=world,
        matter_state=matter,
        producer_state=producers,
        consumer_state=consumers,
        human_state=humans,
    )

    assert "emergence" in report
    assert (world, matter, producers, consumers, humans) == original
