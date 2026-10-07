from __future__ import annotations

import hashlib
import math

from .energy import seasonal_phase, solar_input
from .terrain import lapse_adjustment, latitude_factor


def _unit_noise(seed: str, epoch: int, x: int, y: int) -> float:
    payload = f"{seed}|weather|{epoch}|{x}|{y}".encode("utf-8")
    raw = hashlib.sha256(payload).digest()
    return int.from_bytes(raw[:8], "big") / float(2**64 - 1)


def _signed_noise(seed: str, anchor: int, x: int, y: int) -> float:
    return _unit_noise(seed, anchor, x, y) * 2.0 - 1.0


def persistent_weather_anomaly(
    *,
    seed: str,
    epoch: int,
    ticks_per_year: int,
    x: int,
    y: int,
    channel: str,
) -> float:
    """Deterministic, smoothly persistent weather variation.

    The seasonal cycle remains the climate baseline. This adds a low-frequency
    anomaly whose anchors are about five days apart at the calibrated daily
    timebase. Interpolation makes neighboring ticks correlated rather than
    independently drawing a new weather state every day.
    """
    span = max(2, int(round(ticks_per_year / 73.0)))
    anchor = epoch // span
    position = (epoch % span) / float(span)
    # Smoothstep avoids abrupt slope changes at anchor boundaries.
    blend = position * position * (3.0 - 2.0 * position)
    a = _signed_noise(f"{seed}:{channel}", anchor, x // 4, y // 4)
    b = _signed_noise(f"{seed}:{channel}", anchor + 1, x // 4, y // 4)
    return a * (1.0 - blend) + b * blend




def lightning_activity(
    *,
    seed: str,
    epoch: int,
    ticks_per_year: int,
    x: int,
    y: int,
) -> float:
    """Rare deterministic natural ignition source tied to storm moisture."""
    moisture = persistent_weather_anomaly(
        seed=seed,
        epoch=epoch,
        ticks_per_year=ticks_per_year,
        x=x,
        y=y,
        channel="moisture",
    )
    storminess = max(0.0, moisture)
    strike = _unit_noise(seed + ":lightning", epoch, x, y)
    threshold = 0.992 - min(0.010, storminess * 0.008)
    if strike < threshold:
        return 0.0
    return min(1.0, 0.35 + (strike - threshold) / max(1e-9, 1.0 - threshold) * 0.65)


def temperature_c(
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
    seasonal = 11.0 * math.sin(2.0 * math.pi * (phase - 0.25))
    base = 22.0 - 13.0 * lat
    weather = persistent_weather_anomaly(
        seed=seed,
        epoch=epoch,
        ticks_per_year=ticks_per_year,
        x=x,
        y=y,
        channel="temperature",
    )
    return (
        base
        + seasonal * (0.65 + 0.35 * lat)
        + lapse_adjustment(elevation)
        + weather * 3.5
    )


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
    moisture = persistent_weather_anomaly(
        seed=seed,
        epoch=epoch,
        ticks_per_year=ticks_per_year,
        x=x,
        y=y,
        channel="moisture",
    )
    probability = max(
        0.03,
        min(0.92, 0.23 + 0.18 * wet_season + terrain_lift - 0.08 * lat + 0.08 * moisture),
    )
    u = _unit_noise(seed + ":rain-event", epoch, x, y)
    if u > probability:
        return 0.0
    intensity = 0.5 + 4.5 * _unit_noise(seed + ":intensity", epoch, x, y)
    intensity *= max(0.35, 1.0 + 0.25 * moisture)
    return intensity
