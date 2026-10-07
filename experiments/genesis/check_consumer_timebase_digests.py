"""Ledger digests and fingerprints for fixed configurations (D2 timebase check).

Run on the commit before the D2 correction and on this one, then compare:
  python experiments/genesis/check_consumer_timebase_digests.py before.json          # old commit
  python experiments/genesis/check_consumer_timebase_digests.py after.json           # default
  python experiments/genesis/check_consumer_timebase_digests.py legacy.json legacy   # per-tick-legacy
Expected: legacy == before everywhere; default == before at 12 ticks/year only.
(On the old commit, omit `legacy`: the flag does not exist there.)
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "src"), str(ROOT), str(ROOT / "experiments" / "genesis")]
from hrm_genesis import GenesisConfig, GenesisSimulation
from run_agentus_capacity_multiseed import config_for

legacy = len(sys.argv) > 2
extra = {"consumer_timebase": "per-tick-legacy"} if legacy else {}
cases = {}
for tpy, years in ((12, 30), (24, 10), (36, 6), (365, 1)):
    cfg = GenesisConfig(master_seed="units-check", world_width=6, world_height=6, ticks_per_year=tpy,
                        producer_ecology_enabled=True, consumer_ecology_enabled=True, **extra)
    sim = GenesisSimulation(cfg); sim.run(tpy * years)
    cases[f"eco_tpy{tpy}"] = {"digest": sim.ledger.digest(), "fingerprint": cfg.fingerprint()}
cfg = config_for("agentus-demography-a", "v1")
if legacy:
    cfg = GenesisConfig(**{**cfg.__dict__, **extra})
sim = GenesisSimulation(cfg); sim.run(60)
cases["agentus_v1_60d"] = {"digest": sim.ledger.digest(), "fingerprint": cfg.fingerprint()}
json.dump(cases, open(sys.argv[1], "w"), indent=1)
print(json.dumps(cases, indent=1))
