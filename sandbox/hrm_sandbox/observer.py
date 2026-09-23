"""Read-only observer. Measures and labels; never writes causal state.

Technique labels are produced *after the fact* from whatever (held, verb,
target) keys agents came to value. There is no predefined list.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from .ecology import SEASONS, season_of
from .humans import KNOW, SIG_CODE, describe, sig

if TYPE_CHECKING:
    from .sim import Sim


class Observer:
    def __init__(self, sim: "Sim", frame_every: int = 10):
        self.sim = sim
        self.frame_every = frame_every
        self.frames: list[dict] = []
        self.series: list[dict] = []
        self.events: list[dict] = []
        self.deaths: dict[str, int] = {}
        self.births = 0
        self.first_known: dict[tuple, dict] = {}

    # --- event hooks (called by the sim; they only record) ---------------
    def death(self, hu, cause: str) -> None:
        self.deaths[cause] = self.deaths.get(cause, 0) + 1

    def birth(self, hu) -> None:
        self.births += 1

    def learned(self, hu, key: tuple, source: int) -> None:
        how = "discovered" if source == hu.id else "learned by watching"
        ev = {"t": self.sim.tick, "who": hu.id, "band": hu.band, "from": source,
              "how": how, "what": describe(key), "key": "|".join(key)}
        self.events.append(ev)
        if key not in self.first_known:
            self.first_known[key] = ev

    # --- periodic sampling -------------------------------------------------
    def sample(self) -> None:
        sim = self.sim
        t = sim.tick
        if t % self.frame_every:
            return
        live = [h for h in sim.humans if h.alive]
        prevalence: dict[str, int] = {}
        for h in live:
            for k, v in h.q.items():
                if k[0] != "hand" and v >= KNOW:
                    lbl = "|".join(k)
                    prevalence[lbl] = prevalence.get(lbl, 0) + 1
        bands: dict[int, int] = {}
        for h in live:
            bands[h.band] = bands.get(h.band, 0) + 1
        self.series.append({
            "t": t,
            "season": season_of(t),
            "pop": len(live),
            "bands": bands,
            "rabbits": sum(1 for r in sim.eco.rabbits if r.alive),
            "berries": round(sum(b.berries for b in sim.eco.bushes)),
            "nuts": sum(1 for c in sim.eco.items.values() for i in c if i.kind == "nut"),
            "holding": sum(1 for h in live if h.held is not None),
            "known": prevalence,
        })
        self.frames.append({
            "t": t,
            "h": [[h.x, h.y, h.band, SIG_CODE[sig(h.held)], h.stage, h.id] for h in live],
            "r": [c for r in sim.eco.rabbits if r.alive for c in (r.x, r.y)],
            "b": [int(b.berries) for b in sim.eco.bushes],
            "n": [c for (x, y), cell in sim.eco.items.items()
                  if any(i.kind == "nut" for i in cell) for c in (x, y)],
            "m": [c for (x, y), cell in sim.eco.items.items()
                  if any(i.kind in ("flake", "bound") for i in cell) for c in (x, y)],
        })

    # --- export ------------------------------------------------------------
    def export(self) -> dict:
        sim = self.sim
        labels = {"|".join(k): describe(k) for k in self.first_known}
        for s in self.series:
            for lbl in s["known"]:
                if lbl not in labels:
                    labels[lbl] = describe(tuple(lbl.split("|")))
        return {
            "meta": {"seed": sim.seed, "w": sim.w, "h": sim.h, "ticks": sim.tick,
                     "year": 200, "seasons": list(SEASONS), "frame_every": self.frame_every,
                     "births": self.births, "deaths": self.deaths},
            "terrain": [c for row in sim.terrain for c in row],
            "bushes": [c for b in sim.eco.bushes for c in (b.x, b.y)],
            "trees": [c for p in sim.eco.trees for c in p],
            "frames": self.frames,
            "series": self.series,
            "events": self.events,
            "labels": labels,
        }
