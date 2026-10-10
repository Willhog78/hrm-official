"""Read-only exclusion audit of the live procedural frontier chooser.

No choices, material, instructions or rewards are inserted. Diagnostic fields
never enter Agentus perception/cognition. Run with PYTHONPATH=src:.
python -m qualification.genesis.frontier_exclusions --output result.json
"""

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
import json
from pathlib import Path

from hrm_genesis import GenesisSimulation
from hrm_genesis.human import interactions as cap, transitions as tm
from qualification.genesis.discovery import SEEDS, config_for, reserve_ready
from qualification.genesis.tier_observer import conservation_errors


def physical_differences(remembered, current):
    """Field differences at existing perceptual resolution, not causal labels."""
    fields = set(remembered) | set(current)
    encode = lambda value: json.dumps(value, sort_keys=True, separators=(',', ':'))
    different = {field for field in fields - {'body'}
                 if encode(remembered.get(field)) != encode(current.get(field))}
    if remembered.get('body', [None] * 4)[3:] != current.get('body', [None] * 4)[3:]:
        different.add('injury')
    return sorted(different)


class Exclusions:
    def __init__(self):
        self.calls = Counter()
        self.options = defaultdict(Counter)
        self.closest_mismatch = defaultdict(Counter)
        self.consistency_errors = 0
        self.original = None

    def inspect(self, ctx, options, picked, early, draw):
        if not options:
            self.calls['no_options'] += 1
            return
        if ctx.humans.get('frontier_state_model') != 'procedural-frontier-v1':
            raise ValueError('exclusion audit requires procedural-frontier-v1')
        values = ctx.human['cognition'].get('affordance_values', {})
        ready = all(reserve_ready(ctx))
        state = cap._transition_perception(ctx) if ready else None
        edges = ctx.human['cognition'].get('transition_memory', {}).get('edges', [])
        eligible = []
        for key, spec in options:
            if key not in values:
                status = 'untried_single_action'
            elif not ready:
                status = 'reserve_blocked'
            elif early:
                status = 'preempted:' + early
            else:
                own = [e for e in edges if e['act'] == key]
                matched = [e for e in own if tm.same_procedural_state(e['before'], state)]
                if not own:
                    status = 'no_retained_attempt'
                elif not matched:
                    status = 'physical_state_mismatch'
                    # Closest same-action attempt, ties resolved by stable ID.
                    nearest = min(own, key=lambda e: (len(physical_differences(e['before'], state)), e['id']))
                    self.closest_mismatch[key].update(physical_differences(nearest['before'], state))
                elif not any(e['enabled'] for e in matched):
                    status = 'no_enabled_successor'
                else:
                    promising = any(tm.same_procedural_state(future['before'], prior['after'])
                                    and future['act'] in prior['enabled']
                                    and float(future.get('gain_sum_basal', 0)) > 0
                                    and int(future['n']) < tm.MIN_PLAN_EXPERIENCE
                                    for prior in matched for future in edges)
                    attempts = sum(int(e['n']) for e in matched)
                    limit = cap.SEQUENCE_FRONTIER_LIMIT * (2 if promising else 1)
                    if attempts >= limit:
                        status = 'attempt_budget_exhausted'
                    else:
                        eligible.append(key)
                        if draw is None:
                            status = 'candidate_missing_actual_draw'
                        elif draw >= cap.SEQUENCE_FRONTIER_TRIAL:
                            status = 'candidate_trial_declined'
                        elif picked is not None and picked[0] == key:
                            status = 'candidate_selected'
                        else:
                            status = 'candidate_other_selected'
            self.options[key][status] += 1
        if not early and ready:
            self.calls['frontier_stage_reached'] += 1
            if bool(eligible) != (draw is not None):
                self.consistency_errors += 1
            if eligible:
                self.calls['frontier_candidate_calls'] += 1
                self.calls['frontier_trial_accepted' if draw is not None and draw < cap.SEQUENCE_FRONTIER_TRIAL
                           else 'frontier_trial_declined'] += 1

    def install(self):
        self.original = cap.choose
        original = self.original

        def choose(ctx, options, step, hungry):
            names = ('sequence_choices', 'imitation_tries', 'sequence_exploration')
            before = {name: sum(ctx.stats.get(name, {}).values()) for name in names}
            draws = []
            original_draw = ctx.draw
            had_override = 'draw' in vars(ctx)
            prior_override = vars(ctx).get('draw')

            def observe_draw(*parts):
                result = original_draw(*parts)
                if parts and parts[0] == 'sequence-frontier':
                    draws.append(float(result))
                return result

            ctx.draw = observe_draw
            try:
                picked = original(ctx, options, step, hungry)
            finally:
                if had_override:
                    ctx.draw = prior_override
                else:
                    del ctx.draw
            self.calls['choose_calls'] += 1
            early = None
            for name in ('sequence_choices', 'imitation_tries'):
                if sum(ctx.stats.get(name, {}).values()) > before[name]:
                    early = name
                    break
            values = ctx.human['cognition'].get('affordance_values', {})
            if early is None and picked is not None and picked[0] not in values:
                early = 'ordinary_novelty'
            if early:
                self.calls['early:' + early] += 1
            if len(draws) > 1:
                self.consistency_errors += 1
            self.inspect(ctx, options, picked, early, draws[0] if draws else None)
            if sum(ctx.stats.get('sequence_exploration', {}).values()) > before['sequence_exploration']:
                self.calls['actual_frontier_selections'] += 1
            return picked

        cap.choose = choose

    def uninstall(self):
        if self.original is not None:
            cap.choose = self.original
            self.original = None

    def result(self):
        return {'calls': dict(self.calls), 'option_decisions': {k: dict(v) for k, v in sorted(self.options.items())},
                'closest_same_action_mismatch_fields': {k: dict(v) for k, v in sorted(self.closest_mismatch.items())},
                'consistency_errors': self.consistency_errors}


def run_one(seed, days=365):
    sim = GenesisSimulation(replace(config_for(seed, True), agentus_local_work_enabled=True,
                                    agentus_surface_work_enabled=True, agentus_frontier_state_enabled=True))
    observer = Exclusions()
    observer.install()
    try:
        sim.run(days)
    finally:
        observer.uninstall()
    return {'seed': seed, 'days': days, 'fingerprint': sim.config.fingerprint(),
            'ledger_digest': sim.ledger.digest(), 'ledger_valid': sim.ledger.verify_chain(),
            'conservation': conservation_errors(sim), 'audit': observer.result()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--parallel', type=int, default=3)
    parser.add_argument('--baseline', type=Path, default=Path('experiments/genesis/summaries/FRONTIER_STATE_GATE_2026-10-10.json'))
    args = parser.parse_args()
    baseline = json.loads(args.baseline.read_text())['active']
    with ProcessPoolExecutor(max_workers=args.parallel) as pool:
        rows = list(pool.map(run_one, SEEDS))
    for row in rows:
        prior = next(r for r in baseline if r['seed'] == row['seed'])
        row['prior_ledger_matches'] = row['ledger_digest'] == prior['ledger_digest']
        row['prior_fingerprint_matches'] = row['fingerprint'] == prior['fingerprint']
    passed = all(r['prior_ledger_matches'] and r['prior_fingerprint_matches'] and r['ledger_valid']
                 and not r['audit']['consistency_errors']
                 and max(abs(v) for v in r['conservation'].values()) < 1e-9 for r in rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({'passed': passed, 'read_only': True, 'active': rows}, indent=2) + '\n')
    print(json.dumps({'passed': passed, 'seeds': len(rows)}), flush=True)
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
