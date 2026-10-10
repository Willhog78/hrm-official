"""Opt-in frontier recognition ecological probe and exact opt-out comparisons."""

import argparse
from concurrent.futures import ProcessPoolExecutor
import json
from pathlib import Path

from qualification.genesis.discovery import SEEDS, run_one


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--parallel', type=int, default=3)
    parser.add_argument('--baseline', type=Path, default=Path('experiments/genesis/summaries/INCREMENTAL_INTERLACE_GATE_2026-10-09.json'))
    args = parser.parse_args()
    baseline = json.loads(args.baseline.read_text())['active']
    with ProcessPoolExecutor(max_workers=args.parallel) as pool:
        active_jobs = [pool.submit(run_one, seed, True, 365, observed=True, thermal_exposure=True,
                                  local_work=True, surface_work=True, frontier_state=True) for seed in SEEDS]
        old_jobs = [pool.submit(run_one, seed, True, 365, observed=False,
                               local_work=True, surface_work=True) for seed in SEEDS]
        active = [job.result() for job in active_jobs]
        old = [job.result() for job in old_jobs]
    checks = []
    measured_fields = ('capacity_stats', 'census', 'quarters', 'alive', 'births', 'final_memory',
                       'final_surfaces', 'final_arranged_mass_kg', 'conservation')
    for current in active:
        prior = next(r for r in baseline if r['seed'] == current['seed'])
        current['measured_behavior_matches_prior'] = {field: current[field] == prior[field]
                                                     for field in measured_fields}
    for current in old:
        prior = next(r for r in baseline if r['seed'] == current['seed'])
        checks.append({'seed': current['seed'], 'fingerprint_matches': prior['fingerprint'] == current['fingerprint'],
                       'ledger_matches': prior['ledger_digest'] == current['ledger_digest']})
    passed = (all(c['fingerprint_matches'] and c['ledger_matches'] for c in checks)
              and all(r['ledger_valid'] and max(abs(v) for v in r['conservation'].values()) < 1e-9 for r in active + old)
              and all(r['max_interactions_per_agent_tick'] <= 3 for r in active))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({'passed': passed, 'model': 'procedural-frontier-v1',
                                     'active': active, 'opt_out': old, 'legacy_compatibility': checks}, indent=2) + '\n')
    print(json.dumps({'passed': passed, 'legacy_compatibility': checks}), flush=True)
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
