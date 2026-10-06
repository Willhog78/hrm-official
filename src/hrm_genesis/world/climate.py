from __future__ import annotations

import hashlib
import math

from .energy import seasonal_phase, solar_input
from .terrain import lapse_adjustment, latitude_factor


def _unit_noise(seed: str, epoch: int, x: int, y: int) -> float:
    payload = f"{seed}|weather|{epoch}|{x}|{y}".encode("utf-8")
    raw = hashlib.sha256(payload).digest()
    return int.from_bytes(raw[:8], "big") / float(2**64 - 1)


def temperature_c(
    *,
    epoch: int,
    ticks_per_year: int,
    y: int,
    height: int,
    elevation: float,
) -> float:
    lat = latitude_factor(y, height)
    phase = seasonal_phase(epoch, ticks_per_year)
    seasonal = 11.0 * math.sin(2.0 * math.pi * (phase - 0.25))
    base = 22.0 - 13.0 * lat
    return base + seasonal * (0.65 + 0.35 * lat) + lapse_adjustment(elevation)


def precipitation_amount(
    *,
    seed: str,
    epoch: int,
    ticks_per_year: int,
    x: int,
    y: int,
    height: int,
    elevation: float,
) -> float:
    lat = latitude_factor(y, height)
    phase = seasonal_phase(epoch, ticks_per_year)
    wet_season = 0.55 + 0.45 * math.sin(2.0 * math.pi * (phase + 0.08))
    terrain_lift = min(0.35, elevation / 400.0)
    probability = max(0.05, min(0.85, 0.23 + 0.18 * wet_season + terrain_lift - 0.08 * lat))
    u = _unit_noise(seed, epoch, x, y)
    if u > probability:
        return 0.0
    intensity = 0.5 + 4.5 * _unit_noise(seed + ":intensity", epoch, x, y)
    return intensity
