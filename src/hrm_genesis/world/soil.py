from __future__ import annotations

"""World-side soil context.

Elemental soil inventories and diffusion are owned by hrm_genesis.matter.
This module intentionally contains no nutrient reservoir.
"""


def soil_capacity_factor(elevation: float) -> float:
    """Simple structural terrain modifier reserved for later soil-depth work."""
    return max(0.25, min(1.0, 1.0 - float(elevation) / 500.0))
