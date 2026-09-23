"""Run sandbox simulations and write JSON + one self-contained HTML viewer.

    python -m hrm_sandbox.run --seed 2 4 5 --ticks 6000 --out out/runs.html
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import time

from .sim import Sim

TEMPLATE = Path(__file__).with_name("viewer_template.html")


def summarize(data: dict) -> str:
    s = data["series"][-1]
    lines = [f"seed {data['meta']['seed']}  t={s['t']}  population={s['pop']}  "
             f"rabbits={s['rabbits']}  births={data['meta']['births']}  deaths={data['meta']['deaths']}"]
    for lbl, n in sorted(s["known"].items(), key=lambda kv: -kv[1]):
        lines.append(f"  {n:4d} agents hold: {data['labels'].get(lbl, lbl)}")
    firsts = [e for e in data["events"] if e["how"] == "discovered"]
    lines.append(f"  discoveries={len(firsts)}  social transmissions="
                 f"{sum(1 for e in data['events'] if e['how'] != 'discovered')}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seed", type=int, nargs="+", default=[1])
    ap.add_argument("--ticks", type=int, default=6000)
    ap.add_argument("--bands", type=int, default=4)
    ap.add_argument("--band-size", type=int, default=12)
    ap.add_argument("--frame-every", type=int, default=10)
    ap.add_argument("--out", type=Path, default=Path("out/run.html"))
    args = ap.parse_args(argv)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    runs = []
    for seed in args.seed:
        t0 = time.time()
        sim = Sim(seed=seed, bands=args.bands, band_size=args.band_size,
                  frame_every=args.frame_every)
        for _ in range(args.ticks):
            sim.step()
            if not sim.humans:
                break
        data = sim.observer.export()
        runs.append(data)
        json_path = args.out.with_name(f"{args.out.stem}_seed{seed}.json")
        json_path.write_text(json.dumps(data, separators=(",", ":")))
        print(summarize(data))
        print(f"  wrote {json_path} ({time.time() - t0:.1f}s)")
    payload = json.dumps(runs, separators=(",", ":"))
    args.out.write_text(TEMPLATE.read_text().replace("/*__DATA__*/null", payload))
    print(f"viewer: {args.out}")


if __name__ == "__main__":
    main()
