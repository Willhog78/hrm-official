from __future__ import annotations


def latitude_factor(y: int, height: int) -> float:
    if height <= 1:
        return 0.0
    normalized = y / (height - 1)
    return abs(normalized - 0.5) * 2.0


def lapse_adjustment(elevation: float) -> float:
    # Simplified environmental lapse relationship for the Genesis slice.
    return -0.0065 * elevation
