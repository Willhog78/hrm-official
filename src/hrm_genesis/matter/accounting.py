from __future__ import annotations

from .elements import water_element_mass
from .pools import total_elements, total_water


def water_balance_error(state: dict) -> float:
    stored = total_water(state["cells"])
    expected = (
        float(state["initial_water_kg"])
        + float(state["water_input_kg"])
        - float(state["water_output_kg"])
    )
    return stored - expected


def element_balance_errors(state: dict) -> dict[str, float]:
    current = total_elements(state["cells"])
    initial = {k: float(v) for k, v in state["initial_elements_kg"].items()}
    symbols = sorted(set(current) | set(initial))
    return {
        symbol: current.get(symbol, 0.0) - initial.get(symbol, 0.0)
        for symbol in symbols
    }


def hydrogen_oxygen_open_system_account(state: dict) -> dict[str, float]:
    """Report H/O mass carried by declared water inputs and outputs.

    G1.5 tracks water as a compound reservoir and soil minerals as elemental
    pools. This report exposes the elemental consequence of the open water
    boundary without duplicating H/O into the soil-element inventory.
    """
    incoming = water_element_mass(float(state["water_input_kg"]))
    outgoing = water_element_mass(float(state["water_output_kg"]))
    return {
        "H_net_kg": incoming["H"] - outgoing["H"],
        "O_net_kg": incoming["O"] - outgoing["O"],
    }
