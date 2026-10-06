from __future__ import annotations

import math


def seasonal_phase(epoch: int, ticks_per_year: int) -> float:
    if ticks_per_year <= 0:
        raise ValueError("ticks_per_year must be positive")
    return (epoch % ticks_per_year) / ticks_per_year


def solar_input(epoch: int, ticks_per_year: int, latitude_factor: float) -> float:
    phase = seasonal_phase(epoch, ticks_per_year)
    seasonal = 0.72 + 0.28 * math.sin(2.0 * math.pi * (phase - 0.25))
    latitude = 1.0 - 0.28 * latitude_factor
    return max(0.05, seasonal * latitude)
