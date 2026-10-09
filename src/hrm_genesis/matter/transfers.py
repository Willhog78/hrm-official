from __future__ import annotations

from copy import deepcopy

from hrm_genesis.world.grid import neighbors


SOIL_WATER_CAPACITY_KG = 100.0
MOBILE_ELEMENT_DIFFUSION_RATE = 0.01

# Water-cycle scale (docs/architecture/WATER_CYCLE_SCALE.md). The quantities in
# this water cycle (rain per event, infiltration per day, soil capacity,
# evaporation, the runoff residue) are stated for material scale 1. A world
# whose water and biomass inventories are scaled by `material_scale_factor`
# stores that factor as `water_scale`, and its fluxes and capacities are
# scaled with it so stocks and flows keep the same proportions. Absent (scale
# 1, or "unscaled-legacy") it is 1 and nothing changes.


def water_scale(matter_state: dict) -> float:
    return float(matter_state.get("water_scale", 1.0))


def _lookup(cells: list[dict]) -> dict[tuple[int, int], dict]:
    return {(int(c["x"]), int(c["y"])): c for c in cells}


def apply_water_cycle(
    matter_state: dict,
    world_state: dict,
) -> dict:
    state = deepcopy(matter_state)
    cells = state["cells"]
    width = int(state["width"])
    height = int(state["height"])
    world_lookup = {(int(c["x"]), int(c["y"])): c for c in world_state["cells"]}

    precipitation_total = 0.0
    evaporation_total = 0.0
    scale = water_scale(state)

    for cell in cells:
        xy = (int(cell["x"]), int(cell["y"]))
        climate = world_lookup[xy]
        precipitation = float(climate["precipitation"]) * scale
        precipitation_total += precipitation

        # Snow is a real water reservoir. Existing windless worlds retain the
        # historical rain-only behavior and do not acquire a snow field.
        snow_enabled = "wind_speed_m_s" in climate
        snowfall = precipitation if snow_enabled and float(climate["temperature"]) <= 0.0 else 0.0
        snow = max(0.0, float(cell.get("snow_water_kg", 0.0)))
        if snow_enabled:
            snow += snowfall
            melt = min(snow, scale * 0.08 * max(0.0, float(climate["temperature"])))
            snow -= melt
            cell["snow_water_kg"] = snow
        else:
            melt = 0.0
        surface = float(cell["surface_water_kg"]) + precipitation - snowfall + melt
        soil = float(cell["soil_water_kg"])

        infiltration = min(surface, max(0.0, SOIL_WATER_CAPACITY_KG * scale - soil), 3.0 * scale)
        surface -= infiltration
        soil += infiltration

        evaporation = scale * max(
            0.0,
            0.03 * float(climate["solar"]) + 0.004 * max(float(climate["temperature"]), 0.0),
        )
        # Only opt-in windy worlds provide this field. Move extra actual
        # evaporated water through the existing water_output_kg ledger.
        # The cap avoids an unbounded artificial loss under extreme winds.
        wind_speed = max(0.0, float(climate.get("wind_speed_m_s", 0.0)))
        evaporation *= 1.0 + min(0.6, wind_speed * 0.04)
        from_surface = min(surface, evaporation)
        surface -= from_surface
        remaining = evaporation - from_surface
        from_soil = min(soil, remaining)
        soil -= from_soil
        evaporation_total += from_surface + from_soil

        cell["surface_water_kg"] = surface
        cell["soil_water_kg"] = soil

    lookup = _lookup(cells)
    transfers: dict[tuple[int, int], float] = {}
    terrain = world_lookup
    for cell in cells:
        here = (int(cell["x"]), int(cell["y"]))
        local = float(cell["surface_water_kg"])
        adjacent = neighbors(here[0], here[1], width, height)
        if local <= 0.0 or not adjacent:
            continue
        lowest = min(adjacent, key=lambda xy: float(terrain[xy]["elevation"]))
        if float(terrain[lowest]["elevation"]) >= float(terrain[here]["elevation"]):
            continue
        amount = min(local * 0.18, max(0.0, local - 0.5 * scale))
        if amount <= 0.0:
            continue
        transfers[here] = transfers.get(here, 0.0) - amount
        transfers[lowest] = transfers.get(lowest, 0.0) + amount

    for xy, delta in transfers.items():
        lookup[xy]["surface_water_kg"] = max(
            0.0, float(lookup[xy]["surface_water_kg"]) + delta
        )

    state["water_input_kg"] = float(state["water_input_kg"]) + precipitation_total
    state["water_output_kg"] = float(state["water_output_kg"]) + evaporation_total
    return state


def diffuse_elements(matter_state: dict) -> dict:
    state = deepcopy(matter_state)
    cells = state["cells"]
    width = int(state["width"])
    height = int(state["height"])
    lookup = _lookup(cells)

    symbols = sorted({s for c in cells for s in c["elements_kg"]})
    deltas = {
        (int(c["x"]), int(c["y"])): {symbol: 0.0 for symbol in symbols}
        for c in cells
    }
    seen: set[tuple[tuple[int, int], tuple[int, int]]] = set()

    for cell in cells:
        here = (int(cell["x"]), int(cell["y"]))
        for other in neighbors(here[0], here[1], width, height):
            edge = tuple(sorted((here, other)))
            if edge in seen:
                continue
            seen.add(edge)
            for symbol in symbols:
                a = float(lookup[here]["elements_kg"].get(symbol, 0.0))
                b = float(lookup[other]["elements_kg"].get(symbol, 0.0))
                flow = (a - b) * MOBILE_ELEMENT_DIFFUSION_RATE
                deltas[here][symbol] -= flow
                deltas[other][symbol] += flow

    for xy, element_delta in deltas.items():
        for symbol, delta in element_delta.items():
            lookup[xy]["elements_kg"][symbol] = max(
                0.0, float(lookup[xy]["elements_kg"].get(symbol, 0.0)) + delta
            )
    return state


def evolve_matter(matter_state: dict, world_state: dict, epoch: int) -> dict:
    state = apply_water_cycle(matter_state, world_state)
    state = diffuse_elements(state)
    state["epoch_applied"] = epoch

    for cell in state["cells"]:
        cell["surface_water_kg"] = round(float(cell["surface_water_kg"]), 10)
        cell["soil_water_kg"] = round(float(cell["soil_water_kg"]), 10)
        if "snow_water_kg" in cell:
            cell["snow_water_kg"] = round(float(cell["snow_water_kg"]), 10)
        cell["elements_kg"] = {
            symbol: round(float(amount), 10)
            for symbol, amount in sorted(cell["elements_kg"].items())
        }
    state["water_input_kg"] = round(float(state["water_input_kg"]), 10)
    state["water_output_kg"] = round(float(state["water_output_kg"]), 10)
    return state
