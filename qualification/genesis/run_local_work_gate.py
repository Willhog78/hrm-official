"""Untrained local-work worlds compared with the recorded V4 baseline."""

import argparse
from concurrent.futures import ProcessPoolExecutor
import json
from pathlib import Path

from qualification.genesis.discovery import SEEDS, run_one


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--days', type=int, default=365)
    parser.add_argument('--parallel', type=int, default=4)
    parser.add_argument('--baseline', type=Path, default=Path('experiments/genesis/summaries/DISCOVERY_CENSUS_V4_2026-10-09.json'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.days != 365:
        parser.error('recorded baseline comparison requires 365 days')
    baseline = json.loads(args.baseline.read_text())
    with ProcessPoolExecutor(max_workers=args.parallel) as pool:
        jobs = [pool.submit(run_one, seed, True, args.days, True, True, True) for seed in SEEDS]
        legacy_jobs = [pool.submit(run_one, seed, True, args.days, False) for seed in SEEDS]
        active = [job.result() for job in jobs]
        legacy = [job.result() for job in legacy_jobs]
    # Parent results contain separate observed/unobserved executions.
    old_runs = baseline['rows']
    compatibility = []
    for current in legacy:
        old = next(r for r in old_runs if r['seed'] == current['seed'] and r['weather'] and not r['observed'])
        compatibility.append({'seed': current['seed'], 'fingerprint_matches': old['fingerprint'] == current['fingerprint'],
                              'ledger_matches': old['ledger_digest'] == current['ledger_digest']})
    passed = (all(c['fingerprint_matches'] and c['ledger_matches'] for c in compatibility)
              and all(r['ledger_valid'] and max(abs(v) for v in r['conservation'].values()) < 1e-9 for r in active + legacy)
              and all(r['max_interactions_per_agent_tick'] <= 3 for r in active))
    result = {'passed': passed, 'days': args.days, 'independent_seeds': len(SEEDS),
              'local_work_model': 'local-material-v1', 'legacy_compatibility': compatibility,
              'active': active, 'legacy': legacy}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'passed': passed, 'legacy_compatibility': compatibility}), flush=True)
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
