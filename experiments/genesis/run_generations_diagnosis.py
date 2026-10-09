"""Read-only replay diagnostics; production source and Railway are untouched."""
import argparse, ast, inspect, json, sys, time
from collections import Counter, defaultdict, deque
from copy import deepcopy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT),str(ROOT/'experiments/genesis')]
from hrm_genesis import GenesisSimulation
from qualification.genesis.tier_observer import build_config
from hrm_genesis.world.state import evolve_world
from hrm_genesis.matter.transfers import evolve_matter
from hrm_genesis.ecology.plants import evolve_producers
from hrm_genesis.ecology import animals as animal
from hrm_genesis.human import biology as bio, interactions as cap

parser=argparse.ArgumentParser()
parser.add_argument('--seed',default='c')
parser.add_argument('--years',type=int,default=30)
parser.add_argument('--parity-days',type=int,default=30)
parser.add_argument('--owned-state',action='store_true',help='Diagnostic replay consumes its private states in place; never use with a live fabric')
parser.add_argument('--spatial-index',action='store_true',help='Exact index of animal positions for repeated support queries')
args=parser.parse_args()
config=build_config('agentus-demography-'+args.seed,'v1')


def initial():
    sim=GenesisSimulation(config)
    return [sim.world_state(),sim.matter_state(),sim.ecology_state(),sim.consumer_state(),sim.human_state()]

fast_functions=None
def tick(states,epoch):
    w,m,p,c,h=states
    nw=evolve_world(w,epoch)
    em,ep,ec,eh=fast_functions or (evolve_matter,evolve_producers,animal.evolve_consumers,bio.evolve_agentus_step)
    nm=em(m,w,epoch)
    np,nm=ep(p,nm,w,epoch)
    nc,np,nm=ec(c,np,nm,w,epoch)
    nh,np,nm,nc=eh(h,np,nm,w,epoch,cognition_enabled=config.human_cognition_enabled,actions_enabled=config.human_actions_enabled,consumer_state=nc)
    return [nw,nm,np,nc,nh]

states=initial()
canonical=GenesisSimulation(config)
for epoch in range(args.parity_days):
    states=tick(states,epoch)
    canonical.run(1)
    actual=[canonical.world_state(),canonical.matter_state(),canonical.ecology_state(),canonical.consumer_state(),canonical.human_state()]
    assert states==actual,('parity mismatch',epoch)
print('PARITY_PASS',args.seed,args.parity_days,'complete daily states',flush=True)
del canonical

repro=defaultdict(Counter)
births=[]
parents={}
deaths=[]
history=defaultdict(lambda:deque(maxlen=10))
predators=defaultdict(Counter)
predator_deaths=[]
imitations=defaultdict(Counter)
imitated_keys=defaultdict(set)
deferred=[]
current_epoch=0
spatial_cache={}

def repro_hook(human,survivors,profile,fed_ids,epoch,can_reproduce):
    if human['sex']!='female' or human['age_ticks']<profile['maturity_ticks']:return
    year=epoch//365+1
    males=[p for p in survivors if p['sex']=='male' and p['age_ticks']>=profile['maturity_ticks'] and (p['x'],p['y'])==(human['x'],human['y'])]
    failures=[]
    if not males:failures.append('no_adult_male_in_cell')
    if human['energy']<profile['reproduction_energy_kcal']:failures.append('energy')
    if sum(human['body_elements_kg'].values())<profile['seed_dry_mass_kg']*.9:failures.append('mass')
    if human['id'] not in fed_ids:failures.append('not_fed')
    if epoch-human.get('last_reproduction_epoch',-1000000)<profile['reproduction_cooldown_ticks']:failures.append('cooldown')
    repro[year]['female_days']+=1
    repro[year]['only:'+','.join(failures or ['eligible'])]+=1
    for f in failures:repro[year]['fail:'+f]+=1
    if can_reproduce:
        relationships=[]
        for male in males:
            rel='unresolved'
            if parents.get(male['id'])==human['id']:rel='son'
            elif parents.get(human['id']) and parents.get(human['id'])==parents.get(male['id']):rel='maternal_sibling'
            relationships.append({'id':male['id'],'generation':male['generation'],'relationship':rel})
        births.append({'epoch':epoch,'year':year,'mother':human['id'],'mother_generation':human['generation'],'candidate_males':relationships})

def death_hook(human,dead,effective_profile,caregiver,ate_kg_today,epoch,origin,moved,start_energy,provisioned):
    rec={'epoch':epoch,'age_days':human['age_ticks'],'energy_before':start_energy,'energy_end':human['energy'],'food_kg':ate_kg_today,'body_mass_kg':sum(human['body_elements_kg'].values()),'xy':[human['x'],human['y']],'origin':origin,'moved':moved,'caregiver':None if caregiver is None else {'id':caregiver['id'],'xy':[caregiver['x'],caregiver['y']],'energy':caregiver['energy']},'dependence':effective_profile.get('caregiver_dependence'),'basal':effective_profile['basal_energy_kcal_per_tick'],'nursing_cap':effective_profile.get('nursing_energy_kcal_per_tick',0)*effective_profile.get('nursing_factor',0),'capacity':effective_profile.get('energy_store_capacity_kcal'),'provisioned_mass_water':provisioned}
    history[human['id']].append(rec)
    if dead:deaths.append({'id':human['id'],'generation':human['generation'],'recent_days':list(history[human['id']])})

def predator_hook(a,consumers,predator_hungry,epoch,starved,dehydrated,old,basal_cost):
    if args.spatial_index:
        token=(epoch,id(consumers))
        if spatial_cache.get('token')!=token:
            spatial_cache.clear()
            spatial_cache.update(token=token,positions={x['id']:(x['x'],x['y']) for x in consumers['animals']},counts=Counter((x['x'],x['y']) for x in consumers['animals']))
        old_xy=spatial_cache['positions'][a['id']]
        new_xy=(a['x'],a['y'])
        if old_xy!=new_xy:
            spatial_cache['counts'][old_xy]-=1
            spatial_cache['counts'][new_xy]+=1
            spatial_cache['positions'][a['id']]=new_xy
    if animal.trait_for(a['species']).trophic_role!='predator':return
    year=epoch//365+1
    p=predators[year]
    candidates=animal._prey_candidates(a,consumers)
    p['days']+=1;p['hungry_days']+=int(predator_hungry)
    p['hungry_no_visible_prey']+=int(predator_hungry and not candidates)
    p['hungry_visible_prey']+=int(predator_hungry and bool(candidates))
    p['hungry_prey_in_cell']+=int(predator_hungry and any((x['x'],x['y'])==(a['x'],a['y']) for x in candidates))
    p['max_support_streak']=max(p['max_support_streak'],a.get('support_streak',0))
    if starved or dehydrated or old:predator_deaths.append({'epoch':epoch,'year':year,'id':a['id'],'energy':a['energy'],'visible_prey':len(candidates),'prey_total':sum(animal.trait_for(x['species']).trophic_role!='predator' for x in consumers['animals']),'xy':[a['x'],a['y']]})

instrumented_trees={}
def instrument(module,function_name,target,call):
    cache_key=(module.__name__,function_name)
    tree=instrumented_trees.get(cache_key)
    if tree is None:tree=ast.parse(inspect.getsource(getattr(module,function_name)))
    class Insert(ast.NodeTransformer):
        def visit_Assign(self,node):
            if any(isinstance(t,ast.Name) and t.id==target for t in node.targets):return [node,*ast.parse(call).body]
            return node
    tree=ast.fix_missing_locations(Insert().visit(tree))
    instrumented_trees[cache_key]=tree
    exec(compile(tree,'<audit:'+function_name+'>','exec'),module.__dict__)

bio._audit_repro=repro_hook
bio._audit_death=death_hook
instrument(bio,'evolve_agentus_step','can_reproduce','_audit_repro(human,survivors,profile,fed_ids,epoch,can_reproduce)')
instrument(bio,'evolve_agentus_step','dead','_audit_death(human,dead,effective_profile,caregiver,ate_kg_today,epoch,origin,moved,start_energy,provisioned)')
animal._audit_predator=predator_hook
instrument(animal,'evolve_consumers','old','_audit_predator(animal,consumers,predator_hungry,epoch,starved,dehydrated,old,basal_cost)')

original_learn=cap.learn_from_tick
def learn_wrapper(ctx,intake):
    original_learn(ctx,intake)
    for key,out in ctx.performed:
        if key not in ctx.imitated:continue
        v=ctx.human['cognition']['affordance_values'][key]['v']
        imit=imitations[ctx.epoch//365+1]
        imit['key:'+key]+=1
        imit['paid' if v>0 else 'unpaid']+=1
        imit['created_objects']+=len(out.get('created_classes',[]))
        imit['capture']+=int(bool(out.get('capture')))
        imit['transformed']+=int(bool(out.get('transformed')))
        imit['effort_kcal']+=out.get('effort_kcal',0)
        imitated_keys[ctx.agent_id].add(key)
cap.learn_from_tick=learn_wrapper
original_offspring=bio._offspring
def offspring_wrapper(mother,ordinal,profile):
    child=original_offspring(mother,ordinal,profile)
    parents[child['id']]=mother['id']
    return child
bio._offspring=offspring_wrapper

if args.owned_state:
    # Only remove entry-point copies of exclusively owned component states.
    # All local copies and the old/new climate boundary remain intact.
    from hrm_genesis.matter import transfers
    from hrm_genesis.ecology import plants
    def consume_clone(module,name):
        tree=deepcopy(instrumented_trees.get((module.__name__,name)))
        if tree is None:tree=ast.parse(inspect.getsource(getattr(module,name)))
        class RemoveEntryCopy(ast.NodeTransformer):
            def visit_Call(self,node):
                if isinstance(node.func,ast.Name) and node.func.id=='deepcopy' and len(node.args)==1 and isinstance(node.args[0],ast.Name) and node.args[0].id in ('matter_state','producer_state','consumer_state','human_state'):
                    return node.args[0]
                return self.generic_visit(node)
        tree=ast.fix_missing_locations(RemoveEntryCopy().visit(tree))
        namespace=dict(module.__dict__)
        exec(compile(tree,'<owned-state:'+name+'>','exec'),namespace)
        return namespace[name]
    aw=consume_clone(transfers,'apply_water_cycle')
    diff=consume_clone(transfers,'diffuse_elements')
    em=consume_clone(transfers,'evolve_matter')
    em.__globals__['apply_water_cycle']=aw
    em.__globals__['diffuse_elements']=diff
    fast_functions=(em,consume_clone(plants,'evolve_producers'),consume_clone(animal,'evolve_consumers'),consume_clone(bio,'evolve_agentus_step'))
    if args.spatial_index:
        def indexed_support(a,consumers,producers):
            if 'pcells' not in spatial_cache:spatial_cache['pcells']=animal._cell_lookup(producers['cells'])
            patch=animal._visible_cells(int(a['x']),int(a['y']),int(producers['width']),int(producers['height']),1)
            forage=sum(animal._plant_mass(spatial_cache['pcells'][xy]) for xy in patch)
            competitors=sum(spatial_cache['counts'][xy] for xy in patch)
            result=forage/max(1,competitors)
            if current_epoch%365==0:
                assert result==animal._local_forage_per_consumer(a,consumers,producers),'spatial support mismatch'
            return result
        fast_functions[2].__globals__['_local_forage_per_consumer']=indexed_support

# Check the diagnostic callbacks themselves against the uninstrumented runner.
instrumented_states=initial()
canonical=GenesisSimulation(config)
for epoch in range(args.parity_days):
    instrumented_states=tick(instrumented_states,epoch)
    canonical.run(1)
    assert instrumented_states==[canonical.world_state(),canonical.matter_state(),canonical.ecology_state(),canonical.consumer_state(),canonical.human_state()],('instrumented parity mismatch',epoch)
print('INSTRUMENTED_PARITY_PASS',args.seed,args.parity_days,flush=True)
repro.clear();births.clear();parents.clear();deaths.clear();history.clear();predators.clear();predator_deaths.clear();imitations.clear();imitated_keys.clear()
del canonical,instrumented_states

out=ROOT/'audit-results';out.mkdir(exist_ok=True)
states=initial()
start=time.monotonic()
annual=[]
for epoch in range(args.years*365):
    current_epoch=epoch
    states=tick(states,epoch)
    if (epoch+1)%365==0:
        h=states[4];c=states[3];year=(epoch+1)//365
        positive_copied=[]
        for person in h['humans']:
            for key in imitated_keys[person['id']]:
                v=person.get('cognition',{}).get('affordance_values',{}).get(key,{}).get('v',0)
                if v>0:positive_copied.append({'id':person['id'],'generation':person['generation'],'key':key,'v':v})
        stats=h.get('capacity_stats',{})
        rec={'year':year,'alive':len(h['humans']),'generations':dict(Counter(p['generation'] for p in h['humans'])),'animals':dict(Counter(a['species'] for a in c['animals'])),'deaths':h.get('cumulative_deaths',0),'births':h.get('cumulative_births',0),'captures':stats.get('captures',0),'imitation_tries':sum(stats.get('imitation_tries',{}).values()),'imitation_paid':sum(stats.get('imitation_paid',{}).values()),'reproduction':dict(repro[year]),'predators':dict(predators[year]),'imitation_details':dict(imitations[year]),'positive_copied_keys':positive_copied,'elapsed_s':round(time.monotonic()-start,1)}
        annual.append(rec)
        result={'seed':args.seed,'config_fingerprint':config.fingerprint(),'parity_days':args.parity_days,'annual':annual,'birth_events':births,'death_events':deaths,'predator_deaths':predator_deaths}
        (out/(args.seed+'.json')).write_text(json.dumps(result,indent=2))
        print(json.dumps(rec),flush=True)
        if year in (18,25,30):(out/(args.seed+'-state-y'+str(year)+'.json')).write_text(json.dumps(states))
print('AUDIT_DONE',args.seed,flush=True)
