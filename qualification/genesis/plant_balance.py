"""Plant balance by cell and season (read-only).

One question: why does edible vegetation keep shrinking? For every producer
step, per cell, it records the actual flows (growth, germination, mortality,
seeding) with the rate terms that produced them (light, temperature and water
factors, cell age, stress and old-age mortality), and aggregates them by year
and month, weighted by the living biomass they act on. Climate is also sampled
independently of biomass (every cell, every day) so a change in conditions can
be told apart from a change in where the biomass is.

Mortality is split exactly: the share of each cell-day's dead mass that the
old-age term caused is (1 - f_without / f_with), where f is the per-tick dead
fraction with and without that term (same conversion as the model).

  python -m qualification.genesis.plant_balance --years 10 --seeds agentus-demography-a
  python -m qualification.genesis.plant_balance --years 5 --world   # inhabited world
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for extra in (ROOT / "src", ROOT):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

from hrm_genesis import GenesisSimulation  # noqa: E402
from hrm_genesis.ecology import plants  # noqa: E402
from qualification.genesis.plant_ledger import control_config  # noqa: E402
from qualification.genesis.tier_observer import build_config  # noqa: E402

MONTH_DAYS = 30


def _limiting(light: float, temp: float, water: float) -> str:
    return min((("light", light), ("temp", temp), ("water", water)), key=lambda kv: kv[1])[0]


class Balance:
    def __init__(self, tpy: int) -> None:
        self.tpy = tpy
        self.epoch = 0
        self.month = defaultdict(lambda: defaultdict(float))  # (year, month) -> sums
        self.cell_year = defaultdict(lambda: defaultdict(float))  # (year, xy) -> sums
        self.timebase = plants.PRODUCER_TIMEBASE_ELAPSED

    def key(self):
        day = self.epoch % self.tpy
        return self.epoch // self.tpy + 1, min(11, day // MONTH_DAYS)

    def observe(self, flow: str, kg: float, xy=None, **t) -> None:
        m = self.month[self.key()]
        cy = self.cell_year[(self.epoch // self.tpy + 1, xy)]
        if flow == "growth_edible":
            live = float(t["live_kg"])
            m["growth"] += kg
            m["growth_live"] += live
            for f in ("light", "temp", "water"):
                m[f"w_{f}"] += live * float(t[f])
            m[f"lim_{_limiting(t['light'], t['temp'], t['water'])}"] += live
            m["w_condition"] += live * min(t["light"], t["temp"], t["water"])
            cy["growth"] += kg
        elif flow == "germination":
            m["germination"] += kg
            cy["germination"] += kg
        elif flow == "mortality_edible":
            live = float(t["live_kg"])
            stress, old_age, daily = float(t["stress"]), float(t["old_age"]), float(t["daily"])
            without = min(0.85, plants.BASE_MORTALITY_FRACTION + 0.08 * stress)
            f_with = plants.plant_fraction_per_tick(daily, self.tpy, self.timebase)
            f_without = plants.plant_fraction_per_tick(without, self.tpy, self.timebase)
            share_old = 0.0 if f_with <= 0 else max(0.0, 1.0 - f_without / f_with)
            m["mortality"] += kg
            m["mortality_old_age"] += kg * share_old
            m["mort_live"] += live
            m["w_age"] += live * int(t["age"])
            m["live_over_360"] += live if int(t["age"]) > plants.MAX_AGE_TICKS else 0.0
            m["w_stress_rate"] += live * 0.08 * stress
            m["w_old_rate"] += live * 0.12 * old_age
            cy["mortality"] += kg
            cy["mortality_old_age"] += kg * share_old
            cy["age_sum"] += int(t["age"])
            cy["days"] += 1
        elif flow == "reproduction":
            m["seeding"] += kg
            cy["seeding"] += kg

    def sample_climate(self, world: dict, matter: dict) -> None:
        """Conditions in every cell, independent of where biomass is."""
        m = self.month[self.key()]
        mcells = {(int(c["x"]), int(c["y"])): c for c in matter["cells"]}
        for w in world["cells"]:
            light, temp, water = plants._environment_factors(w, mcells[(int(w["x"]), int(w["y"]))],
                                                             float(matter.get("water_scale", 1.0)))
            m["clim_n"] += 1
            m["clim_condition"] += min(light, temp, water)
            m["clim_light"] += light
            m["clim_temp"] += temp
            m["clim_water"] += water
            c = min(light, temp, water)
            # Days on which a cell's stated daily rates give net growth of
            # standing biomass (growth > base + stress mortality), before
            # seeding (applies at c >= 0.5) and before any old-age term.
            m["clim_net_positive"] += 1 if plants.BASE_GROWTH_FRACTION * c > plants.BASE_MORTALITY_FRACTION + 0.08 * (1 - c) else 0


def run(seed: str, arm: str, years: int, world: bool) -> dict:
    started = time.perf_counter()
    config = build_config(seed, arm) if world else control_config(seed, arm)
    tpy = int(config.ticks_per_year)
    bal = Balance(tpy)
    previous = plants.FLOW_OBSERVER
    plants.FLOW_OBSERVER = bal.observe
    try:
        sim = GenesisSimulation(config)
        for epoch in range(years * tpy):
            bal.epoch = epoch
            sim.run(1)
            bal.sample_climate(sim.world_state(), sim.matter_state())
            if epoch % tpy == tpy - 1:
                print(f"PROGRESS plant-balance {seed}{' world' if world else ' control'} year {epoch // tpy + 1}/{years} "
                      f"{time.perf_counter() - started:.0f}s", flush=True)
        digest = sim.ledger.digest()
    finally:
        plants.FLOW_OBSERVER = previous
    months = []
    for (y, mo), m in sorted(bal.month.items()):
        g, ml = m["growth_live"] or 1e-12, m["mort_live"] or 1e-12
        months.append({
            "year": y, "month": mo + 1,
            "climate": {k: round(m[f"clim_{k}"] / m["clim_n"], 3) for k in ("condition", "light", "temp", "water")},
            "climate_net_positive_share": round(m["clim_net_positive"] / m["clim_n"], 3),
            "biomass_condition": round(m["w_condition"] / g, 3) if m["growth_live"] else None,
            "biomass_limited_by": {k: round(m[f"lim_{k}"] / g, 3) for k in ("light", "temp", "water")} if m["growth_live"] else {},
            "per_kg_day": {"growth": round(m["growth"] / g, 4) if m["growth_live"] else 0.0,
                           "mortality": round(m["mortality"] / ml, 4) if m["mort_live"] else 0.0,
                           "stress_rate": round(m["w_stress_rate"] / ml, 4) if m["mort_live"] else 0.0,
                           "old_age_rate": round(m["w_old_rate"] / ml, 4) if m["mort_live"] else 0.0},
            "biomass_age_days": round(m["w_age"] / ml, 1) if m["mort_live"] else None,
            "share_biomass_over_360_days": round(m["live_over_360"] / ml, 3) if m["mort_live"] else None,
            "kg": {k: round(m[k], 1) for k in ("growth", "germination", "mortality", "mortality_old_age", "seeding")},
        })
    years_out = []
    for y in range(1, years + 1):
        ms = [m for m in months if m["year"] == y]
        tot = {k: sum(m["kg"][k] for m in ms) for k in ("growth", "germination", "mortality", "mortality_old_age", "seeding")}
        cells = [(xy, c) for (yy, xy), c in bal.cell_year.items() if yy == y and xy is not None]
        net = [(c["growth"] + c["germination"] - c["mortality"] - c["seeding"]) for _, c in cells]
        net_no_old = [(c["growth"] + c["germination"] - (c["mortality"] - c["mortality_old_age"]) - c["seeding"]) for _, c in cells]
        years_out.append({
            "year": y, "kg": {k: round(v, 1) for k, v in tot.items()},
            "old_age_share_of_mortality": round(tot["mortality_old_age"] / tot["mortality"], 3) if tot["mortality"] else 0.0,
            "climate_condition": round(sum(m["climate"]["condition"] for m in ms) / len(ms), 3),
            "climate_net_positive_share": round(sum(m["climate_net_positive_share"] for m in ms) / len(ms), 3),
            "cells_net_positive": sum(1 for v in net if v > 0), "cells": len(net),
            "cells_net_positive_without_old_age": sum(1 for v in net_no_old if v > 0),
        })
    return {"seed": seed, "world": world, "years": years, "ledger_digest": digest,
            "fingerprint": config.fingerprint()[:12], "yearly": years_out, "monthly": months,
            "seconds": round(time.perf_counter() - started, 1)}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="plant_balance")
    p.add_argument("--seeds", nargs="*", default=["agentus-demography-a"])
    p.add_argument("--arm", default="v1")
    p.add_argument("--years", type=int, default=10)
    p.add_argument("--world", action="store_true", help="the inhabited world instead of the plant-only control")
    p.add_argument("--json")
    p.add_argument("--check-digest", action="store_true")
    a = p.parse_args(argv)
    results, status = [], 0
    for seed in a.seeds:
        r = run(seed, a.arm, a.years, a.world)
        results.append(r)
        print(f"\n=== plant balance {seed} {'inhabited' if a.world else 'control'} fp {r['fingerprint']} {r['seconds']}s")
        print("  year | kg: growth germination mortality (old-age part) seeding | old-age share | climate condition, "
              "net-positive cell-days | cells net+ (without old age)")
        for y in r["yearly"]:
            k = y["kg"]
            print(f"  y{y['year']:>2} | {k['growth']:>11} {k['germination']:>10} {k['mortality']:>11} ({k['mortality_old_age']:>10}) "
                  f"{k['seeding']:>10} | {y['old_age_share_of_mortality']:>5} | {y['climate_condition']:>5} {y['climate_net_positive_share']:>5} "
                  f"| {y['cells_net_positive']}/{y['cells']} ({y['cells_net_positive_without_old_age']})")
        print("  month | climate cond light temp water net+ | biomass cond limited-by | per kg-day growth mortality "
              "(stress, old age) | biomass age, share >360 d | kg growth mortality seeding")
        for m in r["monthly"]:
            c, pk = m["climate"], m["per_kg_day"]
            print(f"  y{m['year']:>2} m{m['month']:>2} | {c['condition']} {c['light']} {c['temp']} {c['water']} "
                  f"{m['climate_net_positive_share']} | {m['biomass_condition']} {m['biomass_limited_by']} | "
                  f"{pk['growth']} {pk['mortality']} ({pk['stress_rate']}, {pk['old_age_rate']}) | "
                  f"{m['biomass_age_days']} {m['share_biomass_over_360_days']} | {m['kg']['growth']} {m['kg']['mortality']} {m['kg']['seeding']}")
        if a.check_digest:
            cfg = build_config(seed, a.arm) if a.world else control_config(seed, a.arm)
            sim = GenesisSimulation(cfg)
            sim.run(a.years * int(cfg.ticks_per_year))
            same = sim.ledger.digest() == r["ledger_digest"]
            print(f"  read-only: {'IDENTICAL' if same else 'DIFFERENT'} ledger digest")
            status = status or (0 if same else 1)
    if a.json:
        Path(a.json).write_text(json.dumps(results, indent=1))
    print(f"\nRESULT: {'FAIL' if status else 'PASS'}")
    return status


if __name__ == "__main__":
    sys.exit(main())
