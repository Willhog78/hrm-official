"""Read-only work continuity census; observer knowledge never enters cognition.

Run with PYTHONPATH=src:. python -m qualification.genesis.work_continuity
--output result.json. Natural movement and action choices remain unchanged.
"""

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
import json
from pathlib import Path

from hrm_genesis import GenesisSimulation
from hrm_genesis.human import biology, interactions as cap
from qualification.genesis.discovery import SEEDS, config_for, mass, reserve_ready
from qualification.genesis.tier_observer import conservation_errors


class Continuity:
    def __init__(self):
        self.day = 0
        self.counts = Counter()
        self.sites = {}
        self.options = Counter()
        self.selected = Counter()
        self.released_surfaces = {}
        self._seen = set()
        self._originals = []

    def once(self, actor, label):
        token = (actor, self.day, label)
        if token not in self._seen:
            self._seen.add(token)
            self.counts[label] += 1

    def movement(self, human, perception, cognition, target):
        actor = str(human['id'])
        origin = tuple(map(int, perception['origin']))
        site = self.sites.get((actor, origin))
        if site is None:
            return
        self.once(actor, 'movement_decisions_at_own_wood_worksite')
        if site['away']:
            site['returns'] += 1
            site['away'] = False
            self.counts['returns_to_own_wood_worksite'] += 1
        if tuple(target) != origin:
            site['away'] = True
            site['departures'] += 1
            self.counts['departures_from_own_wood_worksite'] += 1
            if site['loose_kg'] > 0:
                self.counts['departures_after_last_observed_loose_wood'] += 1
            here = next(c for c in perception['cells'] if (int(c['x']), int(c['y'])) == origin)
            food = float(here.get('expected_food_kg', here['food_kg']))
            if food >= float(perception.get('forage_need_kg', 0)):
                self.counts['departures_with_locally_adequate_food'] += 1
            if float(here['water_kg']) >= float(perception.get('water_need_kg', 0)):
                self.counts['departures_with_locally_adequate_water'] += 1
            memory = cognition.get('memory', {}).get('locations', {}).get(f'{origin[0]},{origin[1]}', {})
            if memory:
                self.counts['departures_with_location_memory'] += 1
            if 'loose_material_elements_kg' in memory or 'arranged_material_elements_kg' in memory:
                self.counts['departures_with_material_location_memory'] += 1

    def observe_options(self, ctx, options, picked):
        actor = ctx.agent_id
        site = self.sites.get((actor, ctx.xy))
        if site is not None:
            site['loose_kg'] = mass(ctx.pcell.get('loose_material_elements_kg', {}))
            site['arranged_kg'] = mass(ctx.pcell.get('arranged_material_elements_kg', {}))
            self.once(actor, 'interaction_days_at_own_wood_worksite')
        for key, spec in options:
            # Check the actual public interaction key, not guessed intent.
            if key not in {'apply_force:woody|none', 'arrange:loose_wood|none', 'interlace:surface+strands|held'}:
                continue
            self.once(actor, 'offered:' + key)
            self.options[key] += 1
            if all(reserve_ready(ctx)):
                self.once(actor, 'reserve_ready_offered:' + key)
            value = ctx.human['cognition'].get('affordance_values', {}).get(key)
            status = 'untried' if value is None else ('positive' if float(value['v']) > 0 else 'nonpositive')
            self.once(actor, status + '_offered:' + key)
            if picked is not None and picked[0] == key:
                self.selected[key] += 1
                self.once(actor, 'selected:' + key)
                self.once(actor, status + '_selected:' + key)
            elif picked is None:
                self.once(actor, 'no_action_with_option:' + key)
            else:
                self.once(actor, 'other_action_with_option:' + key)

    def after_action(self, ctx, key, before, out):
        if key not in {'apply_force:woody|none', 'arrange:loose_wood|none'}:
            return
        after = (mass(ctx.pcell.get('loose_material_elements_kg', {})),
                 mass(ctx.pcell.get('arranged_material_elements_kg', {})))
        if after == before:
            return
        token = (ctx.agent_id, ctx.xy)
        site = self.sites.setdefault(token, {'first_day': self.day, 'last_day': self.day,
                                            'work_days': set(), 'actions': 0, 'departures': 0,
                                            'returns': 0, 'away': False})
        site.update(last_day=self.day, loose_kg=after[0], arranged_kg=after[1])
        site['work_days'].add(self.day)
        site['actions'] += 1
        self.counts['wood_progress_actions'] += 1

    def surface_action(self, ctx, spec, before):
        if before is None or before.get('material') != 'surface':
            return
        after = next((o for o in ctx.humans.get('objects', []) if o['id'] == before['id']), None)
        token = (ctx.agent_id, before['id'])
        if (spec['verb'] == 'remove_surface' and before.get('holder') == ctx.agent_id
                and before.get('worn') and after is not None and after.get('holder') is None):
            self.released_surfaces[token] = self.day
            self.counts['own_surface_removals'] += 1
        if (spec['verb'] == 'grasp_object' and before.get('holder') is None and after is not None
                and after.get('holder') == ctx.agent_id and token in self.released_surfaces):
            released = self.released_surfaces.pop(token)
            self.counts['own_removed_surface_reacquisitions'] += 1
            if self.day > released:
                self.counts['own_removed_surface_reacquisitions_on_later_day'] += 1

    def install(self):
        original_move, original_choose, original_execute = biology.choose_destination, cap.choose, cap.execute

        def move(human, perception, cognition):
            target = original_move(human, perception, cognition)
            self.movement(human, perception, cognition, target)
            return target

        def choose(ctx, options, step, hungry):
            picked = original_choose(ctx, options, step, hungry)
            self.observe_options(ctx, options, picked)
            return picked

        def execute(ctx, key, spec):
            before = (mass(ctx.pcell.get('loose_material_elements_kg', {})),
                      mass(ctx.pcell.get('arranged_material_elements_kg', {})))
            obj = next((o for o in ctx.humans.get('objects', []) if o['id'] == spec.get('id')), None)
            before_object = dict(obj) if obj is not None else None
            out = original_execute(ctx, key, spec)
            self.after_action(ctx, key, before, out)
            self.surface_action(ctx, spec, before_object)
            return out

        for module, name, wrapper in ((biology, 'choose_destination', move),
                                       (cap, 'choose', choose), (cap, 'execute', execute)):
            self._originals.append((module, name, getattr(module, name)))
            setattr(module, name, wrapper)

    def uninstall(self):
        for module, name, original in reversed(self._originals):
            setattr(module, name, original)
        self._originals.clear()

    def result(self):
        sites = [dict(actor=actor, xy=list(xy), **{k: sorted(v) if isinstance(v, set) else v for k, v in site.items()})
                 for (actor, xy), site in sorted(self.sites.items())]
        return {'counts': dict(self.counts), 'option_decisions': dict(self.options),
                'selected_decisions': dict(self.selected), 'sites': sites,
                'distinct_actor_sites': len(sites),
                'sites_worked_on_multiple_days': sum(len(s['work_days']) > 1 for s in sites),
                'sites_returned_to': sum(s['returns'] > 0 for s in sites)}


def run_one(seed, days=365):
    sim = GenesisSimulation(replace(config_for(seed, True), agentus_local_work_enabled=True,
                                    agentus_surface_work_enabled=True))
    observer = Continuity()
    observer.install()
    try:
        for day in range(1, days + 1):
            observer.day = day
            sim.run(1)
    finally:
        observer.uninstall()
    return {'seed': seed, 'days': days, 'fingerprint': sim.config.fingerprint(),
            'ledger_digest': sim.ledger.digest(), 'ledger_valid': sim.ledger.verify_chain(),
            'conservation': conservation_errors(sim), 'continuity': observer.result()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--parallel', type=int, default=3)
    parser.add_argument('--baseline', type=Path, default=Path('experiments/genesis/summaries/INCREMENTAL_INTERLACE_GATE_2026-10-09.json'))
    args = parser.parse_args()
    baseline = json.loads(args.baseline.read_text())['active']
    with ProcessPoolExecutor(max_workers=args.parallel) as pool:
        rows = list(pool.map(run_one, SEEDS))
    for row in rows:
        prior = next(r for r in baseline if r['seed'] == row['seed'])
        row['prior_ledger_matches'] = row['ledger_digest'] == prior['ledger_digest']
        row['prior_fingerprint_matches'] = row['fingerprint'] == prior['fingerprint']
    passed = all(r['prior_ledger_matches'] and r['prior_fingerprint_matches'] and r['ledger_valid']
                 and max(abs(v) for v in r['conservation'].values()) < 1e-9 for r in rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({'passed': passed, 'read_only': True, 'active': rows}, indent=2) + '\n')
    print(json.dumps({'passed': passed, 'seeds': len(rows)}), flush=True)
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
