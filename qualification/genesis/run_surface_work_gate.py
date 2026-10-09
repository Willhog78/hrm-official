"""Untrained surface-work worlds and explicitly controlled normal-tick wood work."""

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
import json
from pathlib import Path

from hrm_genesis import GenesisSimulation
from hrm_genesis.human import interactions as cap
from qualification.genesis.discovery import SEEDS, config_for, mass, reserve_ready, run_one
from qualification.genesis.tier_observer import conservation_errors


def controlled_wood(seed, days=120):
    """Diagnostic controller selects preparation; every other live process runs.

    Never an autonomous-discovery result. No material/reserves are injected,
    and the actor may move, become unavailable, or fail to accumulate wood.
    """
    config = replace(config_for(seed, True), agentus_local_work_enabled=True,
                     agentus_surface_work_enabled=True)
    sim = GenesisSimulation(config)
    actor = str(sim.human_state()['humans'][0]['id'])
    original = cap.choose
    counts = Counter()
    trajectory = []

    def controlled(ctx, options, step, hungry):
        if ctx.agent_id != actor:
            return original(ctx, options, step, hungry)
        if not all(reserve_ready(ctx)):
            return None
        arranged = mass(ctx.pcell.get('arranged_material_elements_kg', {}))
        loose = mass(ctx.pcell.get('loose_material_elements_kg', {}))
        if arranged >= 30:
            return None
        key = 'arrange:loose_wood|none' if loose + arranged >= 30 else 'apply_force:woody|none'
        picked = next((o for o in options if o[0] == key), None)
        if picked:
            counts[key] += 1
        return picked

    cap.choose = controlled
    try:
        for day in range(1, days + 1):
            sim.run(1)
            cells = sim.ecology_state()['cells']
            people = sim.human_state()['humans']
            person = next((p for p in people if str(p['id']) == actor), None)
            trajectory.append({'day': day,
                               'max_cell_arranged_kg': max(mass(c.get('arranged_material_elements_kg', {})) for c in cells),
                               'max_cell_loose_kg': max(mass(c.get('loose_material_elements_kg', {})) for c in cells),
                               'actor_xy': [person['x'], person['y']] if person else None})
    finally:
        cap.choose = original
    return {'seed': seed, 'days': days, 'controlled_action_selection': True,
            'autonomous_discovery_claim': False, 'actor': actor, 'selected_actions': dict(counts),
            'trajectory': trajectory, 'ledger_valid': sim.ledger.verify_chain(),
            'ledger_digest': sim.ledger.digest(), 'conservation': conservation_errors(sim)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parallel', type=int, default=4)
    parser.add_argument('--baseline', type=Path, default=Path('experiments/genesis/summaries/LOCAL_WORK_GATE_2026-10-09.json'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    baseline = json.loads(args.baseline.read_text())
    with ProcessPoolExecutor(max_workers=args.parallel) as pool:
        jobs = [pool.submit(run_one, seed, True, 365, True, True, True, True) for seed in SEEDS]
        old_jobs = [pool.submit(run_one, seed, True, 365, False, False, True) for seed in SEEDS]
        wood_jobs = [pool.submit(controlled_wood, seed) for seed in SEEDS]
        active = [job.result() for job in jobs]
        old = [job.result() for job in old_jobs]
        wood = [job.result() for job in wood_jobs]
    compatibility = []
    for current in old:
        prior = next(r for r in baseline['active'] if r['seed'] == current['seed'])
        compatibility.append({'seed': current['seed'], 'fingerprint_matches': prior['fingerprint'] == current['fingerprint'],
                              'ledger_matches': prior['ledger_digest'] == current['ledger_digest']})
    passed = (all(c['fingerprint_matches'] and c['ledger_matches'] for c in compatibility)
              and all(r['ledger_valid'] and max(abs(v) for v in r['conservation'].values()) < 1e-9 for r in active + old + wood)
              and all(r['max_interactions_per_agent_tick'] <= 3 for r in active))
    result = {'passed': passed, 'surface_work_model': 'incremental-interlace-v1',
              'independent_ecological_seeds': len(SEEDS), 'active': active, 'opt_out': old,
              'legacy_compatibility': compatibility, 'controlled_wood': wood}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'passed': passed, 'legacy_compatibility': compatibility}), flush=True)
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
