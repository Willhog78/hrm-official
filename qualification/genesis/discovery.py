"""Read-only V4 discovery census. No objects, instructions or rewards are seeded.

Counts local opportunities separately from actual choices, physical progress,
received reward and learned repetition. Paired unobserved runs prove invisibility.
Run: PYTHONPATH=src:. python -m qualification.genesis.discovery --output result.json
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import replace
from copy import deepcopy
import json
from pathlib import Path
import time

from hrm_genesis import GenesisSimulation
from hrm_genesis.human import interactions as cap
from hrm_genesis.human import transitions as tm
from hrm_genesis.human import biology
from qualification.genesis.tier_observer import build_config, conservation_errors


SEEDS = ('agentus-demography-a', 'agentus-demography-b', 'agentus-g10-4-01')


def config_for(seed, weather):
    config = build_config(seed, 'v1-transitionsv4')
    return replace(config, genesis_wind_enabled=weather,
                   agentus_subcell_position_enabled=weather)


def mass(pool):
    return sum(float(v) for v in pool.values())


def reserve_ready(ctx):
    basal = max(1e-9, float(ctx.profile['basal_energy_kcal_per_tick']))
    water_loss = max(1e-9, float(ctx.profile.get('water_loss_per_tick_kg', 1)))
    floor = float(ctx.profile.get('water_capacity_kg', 0)) * float(ctx.profile.get('min_water_fraction', .5))
    return float(ctx.human['energy']) >= 2 * basal, float(ctx.human.get('body_water_kg', 0)) - floor >= 2 * water_loss


class Census:
    def __init__(self, thermal_exposure=False):
        self.thermal_exposure = thermal_exposure
        self.day = 0
        self.counts = Counter()
        self.quarters = defaultdict(Counter)
        self.offered_keys = Counter()
        self.attempts = Counter()
        self.progress = Counter()
        self.effort = Counter()
        self.reward = Counter()
        self.reward_events = Counter()
        self.choice_reasons = Counter()
        self._seen = set()
        self._originals = []
        self._phase = 'other'
        self._per_tick = Counter()

    def tick_metric(self, ctx, label):
        token = (ctx.agent_id, self.day, label)
        if token not in self._seen:
            self._seen.add(token)
            self.counts[label] += 1
            self.quarters[1 + min(3, max(0, self.day - 1) // 92)][label] += 1

    def observe_options(self, ctx, options):
        self.tick_metric(ctx, 'interaction_agent_days')
        energy, water = reserve_ready(ctx)
        self.tick_metric(ctx, 'reserve_ready' if energy and water else 'reserve_blocked')
        if not energy:
            self.tick_metric(ctx, 'energy_guard_blocks_sequence')
        if not water:
            self.tick_metric(ctx, 'water_guard_blocks_sequence')
        if len(ctx.rigid_held()) >= cap.MAX_RIGID_IN_HAND:
            self.tick_metric(ctx, 'rigid_hands_full')
        if len(ctx.soft_held()) >= cap.MAX_SOFT_IN_HAND:
            self.tick_metric(ctx, 'soft_hands_full')
        values = ctx.human['cognition'].get('affordance_values', {})
        if any(key not in values for key, _ in options):
            self.tick_metric(ctx, 'untried_options_present')
        if options and all(key in values for key, _ in options):
            self.tick_metric(ctx, 'all_options_previously_tried')
        local_stones = [o for o in cap.ground_objects(ctx.humans, ctx.xy) if o['material'] == 'stone']
        if len(ctx.mcell_lithics()) + len(local_stones) >= 2:
            self.tick_metric(ctx, 'stone_two_local_targets')
            if cap.available_kg('fresh_tissue', ctx.pcell, ctx.ccell) > 0:
                self.tick_metric(ctx, 'stone_targets_and_fresh_tissue')
        labels = {
            'grasp_natural': 'stone_pickup_offered', 'strike_stone': 'stone_strike_offered',
            'extract_plant_fiber': 'fiber_extraction_offered', 'extract_bark': 'fiber_extraction_offered',
            'extract_tendon': 'fiber_extraction_offered', 'pull_apart': 'fiber_split_offered',
            'twist': 'fiber_twist_offered', 'interlace': 'surface_interlace_offered',
            'wear': 'surface_wear_offered',
        }
        for key, spec in options:
            token = (ctx.agent_id, self.day, 'key:' + key)
            if token not in self._seen:
                self._seen.add(token)
                self.offered_keys[key] += 1
            label = labels.get(spec['verb'])
            if spec['verb'] == 'grasp_object' and key.startswith('grasp:stone'):
                label = 'stone_pickup_offered'
            if label:
                self.tick_metric(ctx, label)
                if energy and water:
                    self.tick_metric(ctx, label + '_reserve_ready')
            if key == 'grasp:stone_edged|none':
                self.tick_metric(ctx, 'stone_edge_pickup_offered')
            if spec['verb'] == 'cut_tissue' and spec.get('tool') is not None:
                self.tick_metric(ctx, 'tool_tissue_cut_offered')
            if key == 'apply_force:woody|none':
                self.tick_metric(ctx, 'wood_force_offered')
                if energy and water:
                    self.tick_metric(ctx, 'wood_force_offered_reserve_ready')
            if key == 'arrange:loose_wood|none':
                self.tick_metric(ctx, 'wood_arrange_offered')
                if energy and water:
                    self.tick_metric(ctx, 'wood_arrange_offered_reserve_ready')

    def install(self):
        observer = self
        original_choose, original_execute = cap.choose, cap.execute
        original_learn, original_heat, original_credit = cap.learn_from_tick, cap.settle_thermal_trials, tm.credit

        def choose(ctx, options, step, hungry):
            observer.observe_options(ctx, options)
            before = {name: sum(ctx.stats.get(name, {}).values())
                      for name in ('sequence_choices', 'sequence_exploration', 'exploit_by_key')}
            picked = original_choose(ctx, options, step, hungry)
            reason = 'none' if picked is None else 'ordinary_explore_retry_or_imitation'
            for name in before:
                if sum(ctx.stats.get(name, {}).values()) > before[name]:
                    reason = name
            observer.choice_reasons[reason] += 1
            if picked is None and options:
                observer.tick_metric(ctx, 'no_choice_with_options')
            if picked is not None:
                observer.tick_metric(ctx, 'at_least_one_action_chosen')
            return picked

        def execute(ctx, key, spec):
            out = original_execute(ctx, key, spec)
            observer.attempts[key] += 1
            observer.effort[key] += float(out['effort_kcal'])
            observer._per_tick[(ctx.agent_id, ctx.epoch)] += 1
            if out.get('transformed') or out.get('created_classes') or out.get('access_bonus_kg', 0) > 0 or out.get('wear_changed'):
                observer.progress[key] += 1
            if out.get('fracture'):
                observer.counts['stone_fractures'] += 1
            if 'stone_edged' in out.get('created_classes', []):
                observer.counts['stone_edges_created'] += 1
            for kind in out.get('created_classes', []):
                if kind.startswith('strand_'):
                    observer.counts['strands_created'] += 1
                elif kind == 'surface':
                    observer.counts['surfaces_created'] += 1
            if out.get('wear_changed'):
                observer.counts['actual_wear_changes'] += 1
            return out

        def phase_call(phase, fn, *args):
            previous = observer._phase
            observer._phase = phase
            try:
                return fn(*args)
            finally:
                observer._phase = previous

        def learn(ctx, intake):
            return phase_call('food', original_learn, ctx, intake)

        def heat(humans, human, epoch, worn_kcal, arrangement_kcal):
            # Raw readouts and credited discounted reward are reported separately.
            observer.counts['worn_readout_kcal'] += float(worn_kcal)
            observer.counts['arrangement_readout_kcal'] += float(arrangement_kcal)
            return phase_call('thermal', original_heat, humans, human, epoch, worn_kcal, arrangement_kcal)

        def credit(cognition, edge_id, gain):
            edge = next((e for e in cognition.get('transition_memory', {}).get('edges', []) if e['id'] == edge_id), None)
            out = original_credit(cognition, edge_id, gain)
            if edge is not None and gain > 0:
                label = observer._phase + ':' + edge['act']
                observer.reward[label] += float(gain)
                observer.reward_events[label] += 1
            return out

        for module, name, wrapper in ((cap, 'choose', choose), (cap, 'execute', execute),
                                       (cap, 'learn_from_tick', learn), (cap, 'settle_thermal_trials', heat),
                                       (tm, 'credit', credit)):
            self._originals.append((module, name, getattr(module, name)))
            setattr(module, name, wrapper)
        if self.thermal_exposure:
            original_physiology = biology._apply_physiology

            def physiology(human, world, moved, *args, **kwargs):
                prior = deepcopy(human)
                out = original_physiology(human, world, moved, *args, **kwargs)
                alternative = dict(kwargs, record_arrangement_benefit=True,
                                   arrangement_reference={'arranged_material_elements_kg': {}, 'arrangement_geometry': {}},
                                   insulation_reference_c=0.0)
                # Readout-only references do not alter actual physics. This
                # separate copy measures all existing protection, including
                # old material whose originating trial has already expired.
                original_physiology(prior, world, moved, *args, **alternative)
                q = 1 + min(3, max(0, observer.day - 1) // 92)
                for label, field, kind in (
                    ('all_worn', 'insulation_saving_kcal', 'worn'),
                    ('all_arrangement', 'arrangement_saving_kcal', 'arrangement')):
                    saving = float(prior.get(field, 0))
                    observer.counts[label + '_saving_kcal'] += saving
                    observer.quarters[q][label + '_saving_kcal'] += saving
                    if saving > 0:
                        observer.counts[label + '_benefit_agent_days'] += 1
                        if kind not in human.get('thermal_trials', {}):
                            observer.counts[label + '_benefit_without_trial_days'] += 1
                if float(human.get('cold_exposure', 0)) > 0:
                    observer.counts['experienced_cold_agent_days'] += 1
                if float(world.get('temperature', 22)) < 16:
                    observer.counts['ambient_below_16C_agent_days'] += 1
                return out

            self._originals.append((biology, '_apply_physiology', original_physiology))
            biology._apply_physiology = physiology

    def uninstall(self):
        for module, name, original in reversed(self._originals):
            setattr(module, name, original)
        self._originals.clear()

    def result(self):
        return {name: dict(getattr(self, name)) for name in (
            'counts', 'offered_keys', 'attempts', 'progress', 'effort', 'reward', 'reward_events', 'choice_reasons')}


def run_one(seed, weather, days, observed=True, thermal_exposure=False, local_work=False):
    started = time.perf_counter()
    config = config_for(seed, weather)
    if local_work:
        config = replace(config, agentus_local_work_enabled=True)
    sim = GenesisSimulation(config)
    census = Census(thermal_exposure)
    initial = sim.human_state()
    if observed:
        census.install()
    try:
        for day in range(1, days + 1):
            census.day = day
            sim.run(1)
    finally:
        if observed:
            census.uninstall()
    state = sim.human_state()
    result = {'seed': seed, 'weather': weather, 'days': days, 'observed': observed,
              'fingerprint': sim.config.fingerprint(), 'ledger_digest': sim.ledger.digest(),
              'ledger_valid': sim.ledger.verify_chain(), 'conservation': conservation_errors(sim),
              'initial_agents': len(initial['humans']), 'alive': len(state['humans']),
              'births': state.get('cumulative_births', 0), 'capacity_stats': state.get('capacity_stats', {}),
              'seconds': round(time.perf_counter() - started, 2)}
    if observed:
        result['census'] = census.result()
        result['quarters'] = {str(q): dict(c) for q, c in census.quarters.items()}
        result['max_interactions_per_agent_tick'] = max(census._per_tick.values(), default=0)
        memories = [p.get('cognition', {}).get('transition_memory', {}) for p in state['humans']]
        result['final_memory'] = {
            'edges': sum(len(m.get('edges', [])) for m in memories),
            'links': sum(len(m.get('links', [])) for m in memories),
            'repeated_links': sum(link['n'] >= tm.MIN_PLAN_EXPERIENCE for m in memories for link in m.get('links', [])),
            'credited_edges': sum(e.get('gain_sum_basal', 0) > 0 for m in memories for e in m.get('edges', [])),
        }
        result['final_surfaces'] = [{'area_m2': o['area_m2'], 'cohesion': o['cohesion'], 'worn': o.get('worn', False)}
                                    for o in state.get('objects', []) if o['material'] == 'surface']
        result['final_arranged_mass_kg'] = sum(mass(c.get('arranged_material_elements_kg', {}))
                                               for c in sim.ecology_state()['cells'])
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--days', type=int, default=365)
    parser.add_argument('--seeds', nargs='+', default=list(SEEDS))
    parser.add_argument('--parallel', type=int, default=4)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--thermal-followup', type=Path,
                        help='Use completed paired census as digest baseline; measure all protection for wind-enabled runs.')
    args = parser.parse_args(argv)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.thermal_followup:
        baseline = json.loads(args.thermal_followup.read_text())
        rows = []
        with ProcessPoolExecutor(max_workers=args.parallel) as pool:
            pending = [pool.submit(run_one, seed, True, args.days, True, True) for seed in args.seeds]
            for future in as_completed(pending):
                row = future.result()
                plain = next(r for r in baseline['rows'] if r['seed'] == row['seed']
                             and r['weather'] and not r['observed'] and r['days'] == args.days)
                row['observer_parity'] = row['ledger_digest'] == plain['ledger_digest'] and row['fingerprint'] == plain['fingerprint']
                rows.append(row)
                args.output.write_text(json.dumps({'rows': rows}, indent=2) + '\n')
                print(f"THERMAL_DONE seed={row['seed']} parity={row['observer_parity']} seconds={row['seconds']}", flush=True)
        passed = all(r['observer_parity'] and r['ledger_valid'] for r in rows)
        args.output.write_text(json.dumps({'passed': passed, 'rows': rows}, indent=2) + '\n')
        return 0 if passed else 1
    jobs = [(seed, weather, args.days, observed) for seed in args.seeds
            for weather in (False, True) for observed in (True, False)]
    rows = []
    with ProcessPoolExecutor(max_workers=args.parallel) as pool:
        pending = {pool.submit(run_one, *job): job for job in jobs}
        for future in as_completed(pending):
            row = future.result()
            rows.append(row)
            args.output.write_text(json.dumps({'model': tm.PROCEDURAL_MODEL, 'rows': rows}, indent=2) + '\n')
            print(f"DONE seed={row['seed']} weather={row['weather']} observed={row['observed']} "
                  f"alive={row['alive']} seconds={row['seconds']}", flush=True)
    observed = [r for r in rows if r['observed']]
    checks = []
    for row in observed:
        plain = next(r for r in rows if not r['observed'] and r['seed'] == row['seed'] and r['weather'] == row['weather'])
        parity = row['ledger_digest'] == plain['ledger_digest']
        row['observer_parity'] = parity
        passed = parity and row['ledger_valid'] and row['max_interactions_per_agent_tick'] <= 3
        passed = passed and row['conservation']['element_rel_error'] < 1e-6 and row['conservation']['water_rel_error'] < 1e-6
        checks.append(passed)
    args.output.write_text(json.dumps({'model': tm.PROCEDURAL_MODEL, 'passed': all(checks),
                                      'rows': sorted(rows, key=lambda r: (r['seed'], r['weather'], r['observed']))}, indent=2) + '\n')
    print(f"DISCOVERY_CENSUS {'PASS' if all(checks) else 'FAIL'} pairs={len(checks)}", flush=True)
    return 0 if all(checks) else 1


if __name__ == '__main__':
    raise SystemExit(main())
