"""Opportunity census for social learning (read-only; ecology opening, step 1).

Following and imitation can only act when the world sets them up. This census
measures, for every independent agent-day, the separate conditions those
mechanisms need, as the agent itself perceives them, and how often they
coincide. It changes nothing: two production functions are wrapped to *look*
at their inputs, each wrapper returns exactly what the original returned, and
`--check-digest` confirms the ledger is identical with and without the census.

Per independent agent-day (the planner is consulted; dependents are carried):

  H  hungry            the planner's own test: forage need > 0, reserve < 0.75
  T  thirst decides    the thirst drive chose today's move (hunger not consulted)
  food known, one of (the planner's order):
     full_in_view      a visible cell covers today's need
     full_remembered   a remembered place (not in view) covers it
     partial_in_view   only a visible cell above the giving-up level (25% of need)
     none              nothing known
  P  peer in view      another individual within perception range (own cell + 4)
  C  peer in own cell  the only place acts can be witnessed
  P_nonkin, C_nonkin   the same, counting only individuals outside the agent's
                       caregiving lineage (caregiver, dependent, same caregiver)
  W  witnessed useful  saw, today, an act with at least one visible consequence
                       (witnessed_salience > 0); `W_nonmeal` excludes acts that
                       are themselves eating
  reserve              energy / satiety reference, the quantity the planner's
                       hunger test thresholds at 0.75; reported in bins, and for
                       agents caring for a dependent that day ("caring")

Useful non-meal acts performed are also counted at the actor, with whether
anyone (or any non-kin) shared the cell: this separates "useful acts are rare"
from "useful acts happen unseen".

Opportunities are counted apart from use:
  follow opportunity   H and not T and food none and P (the branch where
                       following is consulted, with someone to follow)
  follow if partial    H and not T and food partial and P (would exist if the
                       G10.6 partial-food anchor did not come first)
  imitation exposure   W_nonmeal (the raw material imitation draws on)
Use is read from the production stats (follow days, imitation tries).

World context per day: living agents, map-wide edible plant tissue and seed,
and the number of cells holding one adult-day of plant tissue. Everything is
reported by year and by quarter of year (year-days 0-90, 91-181, 182-272,
273-364) so seasonal shortage is not averaged away.

  python -m qualification.genesis.opportunity                 # 4 seeds x 730 days, arm v1
  python -m qualification.genesis.opportunity --days 75 --seeds agentus-demography-a --check-digest
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for extra in (ROOT / "src", ROOT, ROOT / "experiments" / "genesis"):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

import hrm_genesis.human.biology as biology  # noqa: E402
import hrm_genesis.human.interactions as cap  # noqa: E402
import hrm_genesis.human.planning as planning  # noqa: E402
from hrm_genesis import GenesisSimulation  # noqa: E402
from qualification.genesis.tier_observer import build_config, unobserved_digest  # noqa: E402

DEFAULT_SEEDS = ("agentus-demography-a", "agentus-demography-b", "agentus-demography-c", "agentus-demography-d")
DEFAULT_DAYS = 730  # two years: the second winter is where actual shortage was found
QUARTERS = ((0, 90), (91, 181), (182, 272), (273, 364))
FOOD_CLASSES = ("full_in_view", "full_remembered", "partial_in_view", "none")


def _mass(elements: dict) -> float:
    return sum(float(v) for v in elements.values())


def _quarter(year_day: int) -> str:
    for i, (lo, hi) in enumerate(QUARTERS):
        if lo <= year_day <= hi:
            return f"Q{i + 1}"
    return "Q4"


def classify(perception: dict, cognition: dict) -> dict:
    """The conditions the planner faces, from the perception it is given.
    Mirrors the order in planning.choose_destination; calls only pure helpers."""
    need = max(0.0, float(perception.get("forage_need_kg", 0.0)))
    reserve = max(0.0, min(1.0, float(perception.get("energy_reserve_fraction", 1.0))))
    foods = [planning._food(c) for c in perception["cells"]]
    hungry = need > 0.0 and reserve < 0.75
    thirst = planning._thirst_destination(perception, cognition, need, reserve) is not None
    if max(foods) >= need:
        food = "full_in_view"
    elif any(float(f) >= need for _, _, f, _ in perception.get("remembered_food", [])):
        food = "full_remembered"
    elif perception.get("partial_food_anchor") and any(f >= planning.PARTIAL_FOOD_GIVING_UP * need for f in foods):
        food = "partial_in_view"
    else:
        food = "none"
    peers = perception.get("visible_peers") or []
    ox, oy = map(int, perception["origin"])
    return {
        "reserve": reserve,
        "peer_ids": [(str(pid), (int(x), int(y)) == (ox, oy)) for pid, x, y in peers],
        "H": hungry,
        "T": thirst,
        "food": food,
        "P": bool(peers),
        "C": any((int(x), int(y)) == (ox, oy) for _, x, y in peers),
        "peers_tracked": perception.get("visible_peers") is not None,
    }


class Census:
    def __init__(self) -> None:
        self.epoch = 0
        self.day_records: dict[str, dict] = {}
        self.witnessed: dict[str, Counter] = defaultdict(Counter)
        self.caregiver: dict[str, str | None] = {}
        self.acts: Counter = Counter()
        self._originals: list[tuple[object, str, object]] = []

    def install(self) -> None:
        census = self
        original_choose = biology.choose_destination
        original_remember = cap.remember_witnessed

        def choose_destination(human, perception, cognition):
            record = classify(perception, cognition)
            target = original_choose(human, perception, cognition)
            chosen = perception.get("chosen_by")
            record["follow_branch"] = chosen is not None
            record["followed"] = bool(chosen and chosen[0] == "follow")
            census.day_records[str(human["id"])] = record
            return target

        def remember_witnessed(ctx, peer, event, consequence=None):
            # Count what was witnessed, from the arguments: under consequence
            # retention the new event can be the one forgotten at once.
            if ctx.humans.get("event_memory"):
                c = census.witnessed[str(peer["id"])]
                c["any"] += 1
                if cap.witnessed_salience({**event, **(consequence or {})}) > 0:
                    c["useful"] += 1
                    if not str(event["act"]).startswith("eat:"):
                        c["useful_nonmeal"] += 1
            return original_remember(ctx, peer, event, consequence)

        original_observe = cap.observe_outcome

        def observe_outcome(ctx, key, reward=None, visible=None):
            # Every act a capable agent performs passes here (visible-v1), with
            # or without anyone present: count useful acts and their audience.
            if visible is not None:
                salience = cap.witnessed_salience({
                    "act": key, "eaten_kg": visible["eaten_kg"], "hurt": visible["injury"] > 0.0,
                    "appeared": visible.get("appeared", []), "transformed": visible.get("transformed", False),
                    "killed": visible.get("killed", False), "exposed_kg": visible.get("exposed_kg", 0.0)})
                if salience > 0 and not str(key).startswith("eat:"):
                    present = [p for p in ctx.humans["humans"]
                               if p is not ctx.human and "cognition" in p and (int(p["x"]), int(p["y"])) == ctx.xy]
                    kin = [p for p in present if census.related(ctx.agent_id, str(p["id"]))]
                    census.acts["useful_nonmeal_acts"] += 1
                    census.acts["with_audience"] += bool(present)
                    census.acts["with_nonkin_audience"] += len(present) > len(kin)
            return original_observe(ctx, key, reward, visible)

        for module, name, fn in ((biology, "choose_destination", choose_destination),
                                 (cap, "remember_witnessed", remember_witnessed),
                                 (cap, "observe_outcome", observe_outcome)):
            self._originals.append((module, name, getattr(module, name)))
            setattr(module, name, fn)

    def related(self, a: str, b: str) -> bool:
        """Kin by caregiving lineage: caregiver/dependent, or the same caregiver."""
        ca, cb = self.caregiver.get(a), self.caregiver.get(b)
        return ca == b or cb == a or (ca is not None and ca == cb)

    def uninstall(self) -> None:
        for module, name, fn in reversed(self._originals):
            setattr(module, name, fn)
        self._originals.clear()


def _empty_bucket() -> dict:
    return {"agent_days": 0, "dependent_days": 0, "counts": Counter(), "combos": Counter(),
            "world_days": 0, "alive_sum": 0, "plant_kg_sum": 0.0, "seed_kg_sum": 0.0,
            "plant_kg_min": None, "adult_day_cells_min": None, "zero_adult_day_cell_days": 0,
            "dependent_witness_useful": 0}


def _add(bucket: dict, rec: dict) -> None:
    bucket["agent_days"] += 1
    c = bucket["counts"]
    H, T, P, C, food = rec["H"], rec["T"], rec["P"], rec["C"], rec["food"]
    W, Wn = rec["W"] > 0, rec["W_nonmeal"] > 0
    known_full = food in {"full_in_view", "full_remembered"}
    c["H"] += H
    c["T"] += T
    c[f"food:{food}"] += 1
    c["P"] += P
    c["C"] += C
    c["P_nonkin"] += rec["P_nonkin"]
    c["C_nonkin"] += rec["C_nonkin"]
    r = rec["reserve"]
    c["reserve<0.25"] += r < 0.25
    c["reserve<0.50"] += r < 0.50
    c["reserve<0.75"] += r < 0.75
    c["caring"] += rec["caring"]
    c["H_caring"] += H and rec["caring"]
    c["reserve<0.25_caring"] += r < 0.25 and rec["caring"]
    bucket["reserve_sum"] = bucket.get("reserve_sum", 0.0) + r
    c["W"] += W
    c["W_nonmeal"] += Wn
    c["H_and_not_known_full"] += H and not known_full
    c["H_food_none"] += H and food == "none"
    c["H_food_partial"] += H and food == "partial_in_view"
    c["H_and_P"] += H and P
    c["follow_opportunity"] += H and not T and food == "none" and P
    c["follow_if_partial"] += H and not T and food == "partial_in_view" and P
    c["H_not_known_full_and_W"] += H and not known_full and W
    c["follow_branch_reached"] += rec["follow_branch"]
    c["followed"] += rec["followed"]
    # Overlap of the four conditions named in the opening (H, no known full
    # food, peer in view, witnessed useful act), as a 4-bit key.
    bucket["combos"]["".join("1" if b else "0" for b in (H, not known_full, P, W))] += 1


def run_census(seed: str, arm: str, days: int) -> dict:
    started = time.perf_counter()
    census = Census()
    census.install()
    try:
        sim = GenesisSimulation(build_config(seed, arm))
        year = int(sim.config.ticks_per_year)
        profile = sim.human_state()["physiology_profile"]
        adult_need = float(profile["basal_energy_kcal_per_tick"]) / max(
            1e-9, float(profile["food_energy_kcal_per_kg"]) * float(profile["assimilation"]))
        independent = int(profile["independent_feeding_age_ticks"])
        buckets: dict[str, dict] = defaultdict(_empty_bucket)
        peers_tracked = True
        for day in range(days):
            census.day_records = {}
            census.witnessed = defaultdict(Counter)
            census.epoch = day
            census.caregiver = {str(p["id"]): p.get("caregiver_id") for p in sim.human_state()["humans"]}
            sim.run(1)
            state = sim.human_state()
            cells = sim.ecology_state()["cells"]
            plant = [_mass(c["plant_elements_kg"]) for c in cells]
            seed_kg = sum(_mass(c["seed_elements_kg"]) for c in cells)
            adult_day_cells = sum(1 for p in plant if p >= adult_need)
            keys = ("all", f"year{day // year + 1}", f"year{day // year + 1}:{_quarter(day % year)}", f"quarter:{_quarter(day % year)}")
            for key in keys:
                b = buckets[key]
                b["world_days"] += 1
                b["alive_sum"] += len(state["humans"])
                b["plant_kg_sum"] += sum(plant)
                b["seed_kg_sum"] += seed_kg
                b["plant_kg_min"] = sum(plant) if b["plant_kg_min"] is None else min(b["plant_kg_min"], sum(plant))
                b["adult_day_cells_min"] = adult_day_cells if b["adult_day_cells_min"] is None else min(b["adult_day_cells_min"], adult_day_cells)
                b["zero_adult_day_cell_days"] += adult_day_cells == 0
            caring = {str(p.get("caregiver_id")) for p in state["humans"]
                      if int(p["age_ticks"]) < independent and p.get("caregiver_id")}
            for person in state["humans"]:
                pid = str(person["id"])
                rec = census.day_records.get(pid)
                w = census.witnessed.get(pid, Counter())
                if rec is None:
                    if int(person["age_ticks"]) < independent:
                        for key in keys:
                            buckets[key]["dependent_days"] += 1
                            buckets[key]["dependent_witness_useful"] += w["useful"] > 0
                    continue
                peers_tracked = peers_tracked and rec["peers_tracked"]
                nonkin = [(q, same) for q, same in rec["peer_ids"] if not census.related(pid, q)]
                rec = {**rec, "W": w["useful"], "W_nonmeal": w["useful_nonmeal"],
                       "caring": pid in caring,
                       "P_nonkin": bool(nonkin), "C_nonkin": any(same for _, same in nonkin)}
                for key in keys:
                    _add(buckets[key], rec)
        final = sim.human_state()
        stats = final.get("capacity_stats", {})
        result = {
            "seed": seed, "arm": arm, "days": days, "ticks_per_year": year,
            "adult_day_food_kg": round(adult_need, 4),
            "peers_tracked": peers_tracked,
            "ledger_digest": sim.ledger.digest(),
            "ledger_valid": sim.ledger.verify_chain(),
            "alive_end": len(final["humans"]),
            "births": int(final.get("cumulative_births", 0)),
            "deaths_by_cause": dict(final.get("cumulative_deaths_by_cause", {})),
            "use": {
                "follow_days": int(stats.get("follow_days", 0)),
                "follow_outcomes": dict(stats.get("follow_outcomes", {})),
                "imitation_tries": sum(stats.get("imitation_tries", {}).values()),
                "imitation_paid": sum(stats.get("imitation_paid", {}).values()),
            },
            "acts": dict(census.acts),
            "buckets": {k: {**v, "counts": dict(v["counts"]), "combos": dict(v["combos"])} for k, v in buckets.items()},
        }
    except Exception as exc:  # a crash is a result
        import traceback
        result = {"seed": seed, "arm": arm, "days": days, "crash": f"{type(exc).__name__}: {exc}",
                  "traceback": traceback.format_exc(limit=6)}
    finally:
        census.uninstall()
    result["seconds"] = round(time.perf_counter() - started, 1)
    return result


def _job(args: tuple) -> dict:
    return run_census(*args)


def merge(results: list[dict]) -> dict[str, dict]:
    merged: dict[str, dict] = {}
    for r in results:
        for key, b in r.get("buckets", {}).items():
            m = merged.setdefault(key, {**_empty_bucket(), "counts": Counter(), "combos": Counter()})
            for f in ("agent_days", "dependent_days", "world_days", "alive_sum", "plant_kg_sum", "seed_kg_sum",
                      "zero_adult_day_cell_days", "dependent_witness_useful"):
                m[f] += b[f]
            for f in ("plant_kg_min", "adult_day_cells_min"):
                if b[f] is not None:
                    m[f] = b[f] if m[f] is None else min(m[f], b[f])
            m["reserve_sum"] = m.get("reserve_sum", 0.0) + b.get("reserve_sum", 0.0)
            m["counts"].update(b["counts"])
            m["combos"].update(b["combos"])
    return merged


def _pct(n: int, d: int) -> str:
    return f"{n:6d} ({100.0 * n / d:5.1f}%)" if d else f"{n:6d} (  -  )"


def print_report(results: list[dict]) -> None:
    ok = [r for r in results if "crash" not in r]
    for r in results:
        if "crash" in r:
            print(f"CRASH {r['seed']} {r['arm']}: {r['crash']}\n{r['traceback']}")
            continue
        print(f"{r['seed']:24s} {r['arm']:10s} alive {r['alive_end']:3d}  births {r['births']:3d}  deaths {r['deaths_by_cause']}  "
              f"follow days {r['use']['follow_days']}  imitation tries {r['use']['imitation_tries']} (paid {r['use']['imitation_paid']})  "
              f"ledger {'valid' if r['ledger_valid'] else 'INVALID'}  {r['seconds']}s")
    if not ok:
        return
    if not all(r["peers_tracked"] for r in ok):
        print("NOTE: peers are not in perception for this arm (following off); P and C read as 0.")
    merged = merge(ok)
    order = ["all"] + sorted(k for k in merged if k.startswith("quarter:")) + sorted(
        (k for k in merged if k.startswith("year")), key=lambda k: (int(k[4:].split(":")[0]), k))
    print(f"\n== OPPORTUNITY CENSUS: {len(ok)} runs; independent agent-days; percentages of agent-days in the row ==")
    cols = ["H", "T", "food:full_in_view", "food:full_remembered", "food:partial_in_view", "food:none",
            "P", "C", "P_nonkin", "C_nonkin", "W", "W_nonmeal"]
    print(f"{'bucket':16s}{'agent-days':>11s} " + " ".join(f"{c.replace('food:', ''):>17s}" for c in cols))
    for key in order:
        b = merged[key]
        n = b["agent_days"]
        print(f"{key:16s}{n:11d} " + " ".join(f"{_pct(b['counts'].get(c, 0), n):>17s}" for c in cols))
    print("\n-- reserves behind the hunger label (energy / satiety reference; planner calls < 0.75 hungry) --")
    print(f"{'bucket':16s}{'mean':>8s}" + "".join(f"{c:>20s}" for c in ("reserve<0.25", "reserve<0.50", "reserve<0.75", "caring", "H_caring", "reserve<0.25_caring")))
    for key in order:
        b = merged[key]
        n = b["agent_days"]
        print(f"{key:16s}{b.get('reserve_sum', 0.0) / max(1, n):8.2f}" + "".join(
            f"{_pct(b['counts'].get(c, 0), n):>20s}" for c in ("reserve<0.25", "reserve<0.50", "reserve<0.75", "caring", "H_caring", "reserve<0.25_caring")))
    print("\n-- conjunctions --")
    conj = ["H_and_not_known_full", "H_food_partial", "H_food_none", "H_and_P", "follow_if_partial",
            "follow_opportunity", "follow_branch_reached", "followed", "H_not_known_full_and_W"]
    print(f"{'bucket':16s}" + " ".join(f"{c:>23s}" for c in conj))
    for key in order:
        b = merged[key]
        print(f"{key:16s}" + " ".join(f"{_pct(b['counts'].get(c, 0), b['agent_days']):>23s}" for c in conj))
    print("\n-- world context (map-wide; per day) --")
    print(f"{'bucket':16s}{'alive mean':>11s}{'plant kg mean':>15s}{'plant kg min':>14s}{'seed kg mean':>14s}"
          f"{'min cells >= 1 adult-day':>26s}{'days with 0 such cells':>24s}{'dependent-days':>16s}{'dep. saw useful':>16s}")
    for key in order:
        b = merged[key]
        d = max(1, b["world_days"])
        print(f"{key:16s}{b['alive_sum'] / d:11.1f}{b['plant_kg_sum'] / d:15.0f}{(b['plant_kg_min'] or 0):14.0f}"
              f"{b['seed_kg_sum'] / d:14.0f}{(b['adult_day_cells_min'] or 0):26d}{b['zero_adult_day_cell_days']:24d}"
              f"{b['dependent_days']:16d}{b['dependent_witness_useful']:16d}")
    acts = Counter()
    for r in ok:
        acts.update(r.get("acts", {}))
    n = acts.get("useful_nonmeal_acts", 0)
    print(f"\n-- useful non-meal acts performed (any visible consequence): {n}; "
          f"with anyone in the cell {_pct(acts.get('with_audience', 0), n)}; "
          f"with a non-kin in the cell {_pct(acts.get('with_nonkin_audience', 0), n)}")
    print("\n-- overlap, all agent-days: bits = H, no known full food, peer in view, witnessed useful --")
    combos = merged["all"]["combos"]
    total = merged["all"]["agent_days"]
    for bits, n in sorted(combos.items(), key=lambda kv: -kv[1]):
        print(f"  {bits}  {_pct(n, total)}")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="opportunity")
    p.add_argument("--seeds", nargs="*", default=list(DEFAULT_SEEDS))
    p.add_argument("--arm", default="v1")
    p.add_argument("--days", type=int, default=DEFAULT_DAYS)
    p.add_argument("--parallel", type=int, default=4)
    p.add_argument("--json", help="write per-run results here")
    p.add_argument("--check-digest", action="store_true",
                   help="also run each seed unobserved and require identical ledger digests")
    a = p.parse_args(argv)
    t = time.perf_counter()
    jobs = [(seed, a.arm, a.days) for seed in a.seeds]
    if a.parallel <= 1 or len(jobs) == 1:
        results = [_job(j) for j in jobs]
    else:
        with ProcessPoolExecutor(max_workers=min(a.parallel, len(jobs))) as pool:
            results = list(pool.map(_job, jobs))
    print_report(results)
    status = 1 if any("crash" in r or not r.get("ledger_valid", False) for r in results) else 0
    if a.check_digest:
        for r in results:
            if "crash" in r:
                continue
            same = unobserved_digest(r["seed"], r["arm"], r["days"]) == r["ledger_digest"]
            print(f"census non-causal ({r['seed']}): {'IDENTICAL' if same else 'DIFFERENT'} ledger digest")
            status = status or (0 if same else 1)
    if a.json:
        with open(a.json, "w") as fh:
            json.dump(results, fh, indent=1, default=str)
    print(f"\nopportunity census wall time {time.perf_counter() - t:.0f}s  RESULT: {'FAIL' if status else 'PASS'}", flush=True)
    return status


if __name__ == "__main__":
    sys.exit(main())
