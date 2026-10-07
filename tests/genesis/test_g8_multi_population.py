from hrm_coordination.seeds import SeedBank
from hrm_genesis.human.biology import build_human_state
from hrm_genesis.human.regions import POPULATION_IDS, population_counts, region_for_xy


def test_four_founder_populations_begin_in_distinct_regions():
    state = build_human_state(
        width=8,
        height=8,
        seed_bank=SeedBank("g8-test"),
        cognition_enabled=True,
        actions_enabled=True,
        multi_population_enabled=True,
    )

    assert population_counts(state) == {pid: 2 for pid in POPULATION_IDS}

    for human in state["humans"]:
        assert region_for_xy(int(human["x"]), int(human["y"]), 8, 8) == human["population_id"]
