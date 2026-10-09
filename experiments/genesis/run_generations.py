"""Multi-generation daily world: does a second generation appear?

Runs the production configuration (arm `v1`) for many years with the
streaming replay ledger (constant memory), writes a checkpoint every
`--checkpoint-years`, and prints one report per simulated year:

  population   alive by generation; adults and dependents
  adulthood    individuals born in the world who reached maturity this year
  births       by generation of the child (generation >= 2 = descendants of
               world-born parents)
  deaths       by cause, generation and life stage (dependent, juvenile, adult)
  animals      alive by species; births; deaths by cause
  behaviour    captures, imitation tries/paid, following, acts with positive
               learned value, repeated (exploited) acts, worn objects
  plants       edible mass at year end

Nothing is tuned or injected. `--resume CHECKPOINT` continues a run from its
checkpoint (world, Agentus memories, ledger stream and report state).

  python experiments/genesis/run_generations.py --years 25 --seed agentus-demography-a --out runs/gen-a
"""

from __future__ import annotations

import argparse
import json
import resource
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for extra in (ROOT / "src", ROOT):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

from hrm_genesis import GenesisSimulation  # noqa: E402
from hrm_genesis.checkpoint import load_genesis_checkpoint, write_genesis_checkpoint  # noqa: E402
from qualification.genesis.tier_observer import build_config  # noqa: E402


def _mass(elements: dict) -> float:
    return sum(float(v) for v in elements.values())


def _stage(age: int, maturity: int, independent: int) -> str:
    return "adult" if age >= maturity else ("juvenile" if age >= independent else "dependent")


class Reporter:
    """Yearly report state; saved with each checkpoint so a resumed run
    continues the same counters."""

    def __init__(self, state: dict | None = None):
        s = state or {}
        self.seen: dict[str, dict] = s.get("seen", {})           # id -> {generation, age, stage}
        self.recorded_deaths: set[str] = set(s.get("recorded_deaths", []))
        self.prev_stats: dict = s.get("prev_stats", {})
        self.prev_consumers: dict = s.get("prev_consumers", {"births": 0, "deaths": {}})
        self.year_events: dict = s.get("year_events", self._blank())

    @staticmethod
    def _blank() -> dict:
        return {"births": {}, "deaths": [], "new_adults": {}}

    def state(self) -> dict:
        return {"seen": self.seen, "recorded_deaths": sorted(self.recorded_deaths), "prev_stats": self.prev_stats,
                "prev_consumers": self.prev_consumers, "year_events": self.year_events}

    def observe_day(self, h: dict, maturity: int, independent: int) -> None:
        ev = self.year_events
        for p in h["humans"]:
            pid, age, gen = str(p["id"]), int(p["age_ticks"]), int(p.get("generation", 0))
            prev = self.seen.get(pid)
            if prev is None and gen > 0:
                ev["births"][str(gen)] = ev["births"].get(str(gen), 0) + 1
            if prev is not None and gen > 0 and prev["age"] < maturity <= age:
                ev["new_adults"][str(gen)] = ev["new_adults"].get(str(gen), 0) + 1
            self.seen[pid] = {"generation": gen, "age": age, "stage": _stage(age, maturity, independent)}
        for r in h.get("death_records", []):
            rid = str(r["id"])
            if rid in self.recorded_deaths:
                continue
            self.recorded_deaths.add(rid)
            info = self.seen.get(rid, {"generation": int(r.get("generation", 0)), "stage": "unknown"})
            ev["deaths"].append({"cause": r["cause"], "generation": info["generation"], "stage": info["stage"]})
        alive = {str(p["id"]) for p in h["humans"]}
        for pid in [k for k in self.seen if k not in alive and k in self.recorded_deaths]:
            del self.seen[pid]

    def year_report(self, sim: GenesisSimulation, year: int, maturity: int, independent: int) -> dict:
        h, c = sim.human_state(), sim.consumer_state()
        st = h.get("capacity_stats", {})
        people = h["humans"]

        def delta(key):
            return round(float(st.get(key, 0.0)) - float(self.prev_stats.get(key, 0.0)), 3)

        def delta_map(key):
            now, before = Counter(st.get(key, {})), Counter(self.prev_stats.get(key, {}))
            return {k: round(v, 3) for k, v in (now - before).items() if v}

        cdeaths = Counter({k: int(v) for k, v in c.get("cumulative_deaths_by_cause", {}).items()})
        ev = self.year_events
        by_gen = Counter(str(int(p.get("generation", 0))) for p in people)
        stages = Counter(_stage(int(p["age_ticks"]), maturity, independent) for p in people)
        adults_by_gen = Counter(str(int(p.get("generation", 0))) for p in people if int(p["age_ticks"]) >= maturity)
        report = {
            "year": year,
            "alive": len(people),
            "alive_by_generation": dict(sorted(by_gen.items())),
            "alive_by_stage": dict(stages),
            "adults_by_generation": dict(sorted(adults_by_gen.items())),
            "became_adult_by_generation": dict(sorted(ev["new_adults"].items())),
            "births_by_child_generation": dict(sorted(ev["births"].items())),
            "descendant_births": sum(v for g, v in ev["births"].items() if int(g) >= 2),
            "deaths": dict(Counter(f"{d['cause']}|gen{d['generation']}|{d['stage']}" for d in ev["deaths"])),
            "max_generation": max((int(p.get("generation", 0)) for p in people), default=0),
            "oldest_world_born_years": round(max((int(p["age_ticks"]) for p in people if int(p.get("generation", 0)) > 0),
                                                 default=0) / float(sim.config.ticks_per_year), 1),
            "animals": dict(sorted(Counter(a["species"] for a in c["animals"]).items())),
            "animal_births": int(c.get("cumulative_births", 0)) - int(self.prev_consumers.get("births", 0)),
            "animal_deaths": {k: v for k, v in (cdeaths - Counter(self.prev_consumers.get("deaths", {}))).items() if v},
            "captures": delta("captures"),
            "imitation_tries": sum(delta_map("imitation_tries").values()),
            "imitation_paid": sum(delta_map("imitation_paid").values()),
            "follow_days": delta("follow_days"),
            "repeated_acts": delta_map("exploit_by_key"),
            "positive_acts_living": dict(Counter(
                k for p in people for k, e in p.get("cognition", {}).get("affordance_values", {}).items()
                if float(e["v"]) > 0).most_common(8)),
            "worn_objects": sum(1 for o in h.get("objects", []) if o.get("worn")),
            "objects": len(h.get("objects", [])),
            "insulation_saving_kcal": delta("insulation_saving_kcal"),
            "edible_plant_t": round(sum(_mass(cell["plant_elements_kg"]) for cell in sim.ecology_state()["cells"]) / 1000.0, 1),
        }
        self.prev_stats = {**{k: (dict(v) if isinstance(v, dict) else v) for k, v in st.items()}}
        self.prev_consumers = {"births": int(c.get("cumulative_births", 0)), "deaths": dict(cdeaths)}
        self.year_events = self._blank()
        return report


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--years", type=int, default=25, help="run until this simulated year")
    p.add_argument("--seed", default="agentus-demography-a")
    p.add_argument("--arm", default="v1")
    p.add_argument("--out", required=True, help="directory for the ledger stream, checkpoints and reports")
    p.add_argument("--checkpoint-years", type=int, default=5)
    p.add_argument("--ledger-codec", choices=("gzip", "xz"), default="xz")
    p.add_argument("--ledger-group-epochs", type=int, default=30,
                   help="epochs per compressed member (day-to-day similarity compresses well)")
    p.add_argument("--keep-checkpoints", type=int, default=2, help="keep only the newest N checkpoints (disk)")
    p.add_argument("--stop-at-disk-gb", type=float, default=0.0,
                   help="if the filesystem holding --out has used more than this, checkpoint and stop cleanly")
    p.add_argument("--resume", help="checkpoint file to continue from")
    p.add_argument("--auto-resume", action="store_true",
                   help="continue from the latest checkpoint in --out if there is one (survives runner restarts)")
    a = p.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    if a.auto_resume and not a.resume:
        latest = sorted(c for c in out.glob("checkpoint_y*.json") if c.name.count(".") == 1)
        if latest:
            a.resume = str(latest[-1])
            # Reports written after that checkpoint are re-run and rewritten.
            year = int(latest[-1].stem.split("_y")[1])
            reports = out / "yearly_reports.jsonl"
            if reports.exists():
                kept = [l for l in reports.read_text().splitlines() if l and json.loads(l)["year"] <= year]
                reports.write_text("".join(k + "\n" for k in kept))
    config = build_config(a.seed, a.arm)
    if a.resume:
        sim = load_genesis_checkpoint(a.resume, config)
        reporter = Reporter(json.loads(Path(a.resume + ".report.json").read_text()))
    else:
        sim = GenesisSimulation(config, ledger_path=str(out / f"ledger.jsonl.{'xz' if a.ledger_codec == 'xz' else 'gz'}"),
                                ledger_group_epochs=a.ledger_group_epochs, ledger_codec=a.ledger_codec)
        reporter = Reporter()
    tpy = int(config.ticks_per_year)
    profile = sim.human_state()["physiology_profile"]
    maturity, independent = int(profile["maturity_ticks"]), int(profile["independent_feeding_age_ticks"])
    start_year = int(sim.orchestrator.epoch) // tpy
    started = time.perf_counter()
    print(f"GENERATIONS_START seed={a.seed} arm={a.arm} fp={config.fingerprint()[:12]} from_year={start_year} to_year={a.years}",
          flush=True)
    reports_path = out / "yearly_reports.jsonl"
    for year in range(start_year + 1, a.years + 1):
        for _ in range(tpy):
            sim.run(1)
            reporter.observe_day(sim.human_state(), maturity, independent)
        r = reporter.year_report(sim, year, maturity, independent)
        r["peak_rss_gb"] = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6, 2)
        r["ledger_digest"] = sim.ledger.digest()[:16]
        r["disk_mb"] = round(sum(f.stat().st_size for f in out.iterdir() if f.is_file()) / 1e6, 1)
        with reports_path.open("a") as f:
            f.write(json.dumps(r) + "\n")
        print(f"YEAR {a.seed} {json.dumps(r, separators=(',', ':'))}", flush=True)
        import shutil
        disk_full = a.stop_at_disk_gb > 0 and shutil.disk_usage(out).used / 1e9 > a.stop_at_disk_gb
        if year % a.checkpoint_years == 0 or year == a.years or disk_full:
            ck = out / f"checkpoint_y{year:03d}.json"
            write_genesis_checkpoint(ck, sim)
            Path(str(ck) + ".report.json").write_text(json.dumps(reporter.state()))
            print(f"CHECKPOINT {a.seed} year={year} path={ck} {time.perf_counter() - started:.0f}s", flush=True)
            for old in sorted(c for c in out.glob("checkpoint_y*.json") if c.name.count(".") == 1)[:-max(1, a.keep_checkpoints)]:
                old.unlink()
                Path(str(old) + ".report.json").unlink(missing_ok=True)
        if disk_full:
            print(f"STOPPED_DISK {a.seed} year={year} used_gb={shutil.disk_usage(out).used / 1e9:.2f}", flush=True)
            return 0
    print(f"GENERATIONS_DONE seed={a.seed} years={a.years} digest={sim.ledger.digest()} "
          f"{time.perf_counter() - started:.0f}s", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
