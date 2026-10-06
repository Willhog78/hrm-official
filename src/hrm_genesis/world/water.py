from __future__ import annotations

from .grid import by_coordinate, neighbors


SOIL_CAPACITY = 100.0


def apply_hydrology(cells: list[dict], width: int, height: int) -> tuple[float, float]:
    """Apply infiltration, evaporation and bounded downhill runoff.

    Returns (evaporation_loss, runoff_boundary_loss). The Genesis G1 world is
    bounded, so boundary runoff is currently zero by contract.
    """
    evaporation_loss = 0.0

    for cell in cells:
        surface = float(cell["surface_water"]) + float(cell["precipitation"])
        soil = float(cell["soil_moisture"])

        infiltration = min(surface, max(0.0, SOIL_CAPACITY - soil), 3.0)
        surface -= infiltration
        soil += infiltration

        temp = float(cell["temperature"])
        solar = float(cell["solar"])
        evaporation = max(0.0, 0.03 * solar + 0.004 * max(temp, 0.0))
        from_surface = min(surface, evaporation)
        surface -= from_surface
        remaining = evaporation - from_surface
        from_soil = min(soil, remaining)
        soil -= from_soil
        evaporation_loss += from_surface + from_soil

        cell["surface_water"] = surface
        cell["soil_moisture"] = soil

    lookup = by_coordinate(cells)
    transfers: dict[tuple[int, int], float] = {}
    for cell in cells:
        x, y = int(cell["x"]), int(cell["y"])
        local = float(cell["surface_water"])
        if local <= 0.0:
            continue
        adjacent = neighbors(x, y, width, height)
        if not adjacent:
            continue
        lowest = min(adjacent, key=lambda xy: float(lookup[xy]["elevation"]))
        if float(lookup[lowest]["elevation"]) >= float(cell["elevation"]):
            continue
        amount = min(local * 0.18, max(0.0, local - 0.5))
        if amount <= 0.0:
            continue
        transfers[(x, y)] = transfers.get((x, y), 0.0) - amount
        transfers[lowest] = transfers.get(lowest, 0.0) + amount

    for xy, delta in transfers.items():
        lookup[xy]["surface_water"] = max(0.0, float(lookup[xy]["surface_water"]) + delta)

    return evaporation_loss, 0.0
