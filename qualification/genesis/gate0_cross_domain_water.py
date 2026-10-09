"""Read-only, short cross-authority water/replay gate (not a Railway run)."""
from __future__ import annotations

import argparse
import tempfile
from pathlib import Path
from hrm_genesis import GenesisConfig, GenesisSimulation
from hrm_genesis.matter.pools import total_water
from hrm_genesis.ecology.animals import consumer_water_total_kg
from hrm_genesis.human.biology import human_water_total_kg


def water_error(sim: GenesisSimulation) -> float:
    matter = sim.matter_state()
    stored = (total_water(matter['cells'])
              + consumer_water_total_kg(sim.consumer_state())
              + human_water_total_kg(sim.human_state()))
    expected = (float(matter['initial_water_kg'])
                + float(matter['water_input_kg'])
                - float(matter['water_output_kg']))
    return stored - expected


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--days', type=int, default=8)
    args = parser.parse_args()
    config = GenesisConfig(master_seed='gate0-cross-domain-water', world_width=4,
                           world_height=4, ticks_per_year=365,
                           material_scale_factor=1000.0,
                           producer_ecology_enabled=True, consumer_ecology_enabled=True,
                           human_biology_enabled=True, human_cognition_enabled=True,
                           human_actions_enabled=True, human_calibration_enabled=True,
                           agentus_capacities_enabled=True)
    baseline = GenesisSimulation(config)
    cut = max(1, args.days // 2)
    errors = [water_error(baseline)]
    with tempfile.TemporaryDirectory() as d:
        for _ in range(cut):
            baseline.run(1)
            errors.append(water_error(baseline))
        path = Path(d) / 'gate0.json'
        baseline.write_checkpoint(path)
        restored = GenesisSimulation.load_checkpoint(path, config)
        for _ in range(args.days - cut):
            baseline.run(1)
            restored.run(1)
            errors.append(water_error(baseline))
        assert baseline.human_state() == restored.human_state(), 'human checkpoint mismatch'
        assert baseline.matter_state() == restored.matter_state(), 'matter checkpoint mismatch'
        assert baseline.consumer_state() == restored.consumer_state(), 'consumer checkpoint mismatch'
        assert baseline.ledger.digest() == restored.ledger.digest(), 'ledger mismatch'
        assert baseline.ledger.verify_chain() and restored.ledger.verify_chain()
    maximum = max(map(abs, errors))
    print(f'WATER_MAX_ABS_ERROR_KG={maximum:.9f}')
    print(f'REPLAY_PASS days={args.days} cut={cut}')
    assert maximum < 1e-5, f'whole-domain water mismatch {maximum:.9f} kg'


if __name__ == '__main__':
    main()
