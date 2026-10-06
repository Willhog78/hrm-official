from __future__ import annotations

"""G2 decomposition contract.

Decomposition is implemented inside the atomic producer step so dead producer
matter and Matter nutrient return cannot diverge across two transactions.

This module exposes only the governing invariant for tests/documentation.
"""


def decomposition_returns_to_matter() -> bool:
    return True
