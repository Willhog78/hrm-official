from __future__ import annotations

"""World-side hydrology geometry helpers.

Material water inventory and transfer are owned by hrm_genesis.matter.
This module must not mutate water mass.
"""


def downhill_target(
    *,
    x: int,
    y: int,
    elevations: dict[tuple[int, int], float],
    neighbors: tuple[tuple[int, int], ...],
) -> tuple[int, int] | None:
    if not neighbors:
        return None
    lowest = min(neighbors, key=lambda xy: elevations[xy])
    if elevations[lowest] >= elevations[(x, y)]:
        return None
    return lowest
