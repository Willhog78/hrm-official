from __future__ import annotations

import random
import types

import pytest

from hrm_matter import (
    ELEMENT_TABLE,
    MatterEntity,
    MatterKernel,
    Phase,
    ConservationError,
    PropertyError,
    composition_digest,
)
from hrm_matter.entities import CompositionError
from hrm_matter.transform import split, merge, add_energy


def water_ish(mass=1.0, energy=0.0):
    return MatterEntity(composition={"H": 0.111, "O": 0.889}, mass_kg=mass, internal_energy_j=energy)


def iron_bar(mass=1.0, energy=0.0):
    return MatterEntity(composition={"Fe": 1.0}, mass_kg=mass, internal_energy_j=energy)


# ---------------------------------------------------------------------------
# M2.1 -- composition realism, not an opaque ID
# ---------------------------------------------------------------------------

def test_m2_1_identical_composition_is_physically_interchangeable():
    a = MatterEntity(composition={"Fe": 1.0}, mass_kg=2.0, internal_energy_j=100.0)
    b = MatterEntity(composition={"Fe": 1.0}, mass_kg=2.0, internal_energy_j=100.0)
    assert a == b
    assert composition_digest(a) == composition_digest(b)


def test_m2_1_different_composition_is_not_equal():
    assert water_ish() != iron_bar()


def test_m2_1_unknown_element_rejected():
    with pytest.raises(PropertyError):
        MatterEntity(composition={"Unobtainium": 1.0}, mass_kg=1.0, internal_energy_j=0.0)


def test_m2_1_composition_must_sum_to_one():
    with pytest.raises(CompositionError):
        MatterEntity(composition={"Fe": 0.5, "H": 0.2}, mass_kg=1.0, internal_energy_j=0.0)


# ---------------------------------------------------------------------------
# M2.2 / M2.3 -- mass and energy conservation
# ---------------------------------------------------------------------------

def test_m2_2_m2_3_split_conserves_mass_and_energy():
    e = water_ish(mass=10.0, energy=5000.0)
    parts = split(e, [0.25, 0.25, 0.5])
    assert abs(sum(p.mass_kg for p in parts) - 10.0) < 1e-9
    assert abs(sum(p.internal_energy_j for p in parts) - 5000.0) < 1e-9


def test_m2_2_m2_3_merge_conserves_mass_and_energy():
    a = water_ish(mass=3.0, energy=100.0)
    b = iron_bar(mass=7.0, energy=900.0)
    m = merge([a, b])
    assert abs(m.mass_kg - 10.0) < 1e-9
    assert abs(m.internal_energy_j - 1000.0) < 1e-9


def test_m2_2_add_energy_never_creates_or_destroys_mass():
    e = water_ish(mass=1.0, energy=0.0)
    hotter = add_energy(e, 500.0)
    assert hotter.mass_kg == e.mass_kg
    assert hotter.internal_energy_j == 500.0
    with pytest.raises(ConservationError):
        add_energy(hotter, -10_000.0)  # cannot remove more energy than present


# ---------------------------------------------------------------------------
# M2.4 -- phase is derived, never authored
# ---------------------------------------------------------------------------

def test_m2_4_phase_has_no_setter():
    e = water_ish()
    with pytest.raises(AttributeError):
        e.phase = Phase.GAS  # frozen dataclass; direct assignment must fail


def test_m2_4_phase_changes_only_by_crossing_thresholds():
    e = iron_bar(mass=1.0, energy=0.0)
    assert e.phase == Phase.SOLID
    just_under = add_energy(e, e.melt_complete_j_per_kg - 1.0)
    assert just_under.phase == Phase.SOLID
    just_over = add_energy(e, e.melt_complete_j_per_kg + 1.0)
    assert just_over.phase == Phase.LIQUID
    boiled = add_energy(e, e.boil_complete_j_per_kg + 1.0)
    assert boiled.phase == Phase.GAS


# ---------------------------------------------------------------------------
# M2.5 -- split has no privileged parent
# ---------------------------------------------------------------------------

def test_m2_5_split_parts_are_equal_standing_and_share_composition():
    e = water_ish(mass=4.0, energy=800.0)
    parts = split(e, [0.5, 0.5])
    assert parts[0].composition == parts[1].composition == e.composition
    assert parts[0] == MatterEntity(composition=e.composition, mass_kg=2.0, internal_energy_j=400.0)


def test_m2_5_split_into_one_is_identity():
    e = water_ish(mass=5.0, energy=250.0)
    (only,) = split(e, [1.0])
    assert only == e


def test_m2_5_split_into_large_n():
    e = iron_bar(mass=1000.0, energy=50_000.0)
    n = 500
    parts = split(e, [1.0 / n] * n)
    assert len(parts) == n
    assert abs(sum(p.mass_kg for p in parts) - 1000.0) < 1e-6
    assert abs(sum(p.internal_energy_j for p in parts) - 50_000.0) < 1e-6


# ---------------------------------------------------------------------------
# M2.6 -- merge is order-independent and composition-correct
# ---------------------------------------------------------------------------

def test_m2_6_merge_composition_is_mass_weighted():
    a = MatterEntity(composition={"Fe": 1.0}, mass_kg=1.0, internal_energy_j=0.0)
    b = MatterEntity(composition={"H": 1.0}, mass_kg=3.0, internal_energy_j=0.0)
    m = merge([a, b])
    assert abs(m.composition["Fe"] - 0.25) < 1e-9
    assert abs(m.composition["H"] - 0.75) < 1e-9


def test_m2_6_merge_is_order_independent_to_tolerance():
    entities = [
        MatterEntity(composition={"Fe": 0.6, "H": 0.4}, mass_kg=3.0, internal_energy_j=120.0),
        MatterEntity(composition={"O": 1.0}, mass_kg=1.5, internal_energy_j=40.0),
        MatterEntity(composition={"C": 0.3, "Au": 0.7}, mass_kg=7.0, internal_energy_j=900.0),
    ]
    forward = merge(entities)
    reversed_order = merge(list(reversed(entities)))
    assert abs(forward.mass_kg - reversed_order.mass_kg) < 1e-9
    assert abs(forward.internal_energy_j - reversed_order.internal_energy_j) < 1e-9
    for sym in forward.composition:
        assert abs(forward.composition[sym] - reversed_order.composition.get(sym, 0.0)) < 1e-9


def test_m2_6_split_then_merge_round_trip():
    e = MatterEntity(composition={"Fe": 0.3, "C": 0.7}, mass_kg=12.0, internal_energy_j=3000.0)
    parts = split(e, [0.2, 0.3, 0.5])
    back = merge(list(parts))
    assert abs(back.mass_kg - e.mass_kg) < 1e-6
    assert abs(back.internal_energy_j - e.internal_energy_j) < 1e-6
    for sym in e.composition:
        assert abs(back.composition[sym] - e.composition[sym]) < 1e-6


# ---------------------------------------------------------------------------
# M2.7 -- ownership boundary
# ---------------------------------------------------------------------------

def test_m2_7_port_has_no_register_and_cannot_conjure_matter():
    kernel = MatterKernel()
    port = kernel.port()
    assert not hasattr(port, "register")


def test_m2_7_port_operations_use_declared_interface_only():
    kernel = MatterKernel()
    eid = kernel.register(water_ish(mass=2.0, energy=10.0))
    port = kernel.port()
    fetched = port.get(eid)
    assert fetched == water_ish(mass=2.0, energy=10.0)
    ids = port.split(eid, (0.5, 0.5))
    assert len(ids) == 2
    with pytest.raises(KeyError):
        port.get(eid)  # original id retired after split, per M2.5


# ---------------------------------------------------------------------------
# M2.8 -- determinism
# ---------------------------------------------------------------------------

def test_m2_8_same_operations_produce_identical_digest():
    def run():
        kernel = MatterKernel()
        eid = kernel.register(MatterEntity(composition={"Fe": 0.5, "C": 0.5}, mass_kg=10.0, internal_energy_j=1000.0))
        a, b = kernel.apply_split(eid, (0.4, 0.6))
        heated = kernel.apply_add_energy(a, 250.0)
        merged = kernel.apply_merge((heated, b))
        return kernel.state_digest()

    assert run() == run()


# ---------------------------------------------------------------------------
# M2.9 -- no name-based special cases
# ---------------------------------------------------------------------------

def test_m2_9_transform_module_has_no_element_name_literals():
    import inspect
    from hrm_matter import transform as transform_module
    source = inspect.getsource(transform_module)
    for symbol in ELEMENT_TABLE:
        assert f'"{symbol}"' not in source and f"'{symbol}'" not in source, (
            f"transform.py contains a literal reference to element {symbol!r}"
        )


# ---------------------------------------------------------------------------
# M2.10 -- conservation under adversarial composition
# ---------------------------------------------------------------------------

def test_m2_10_zero_mass_entities():
    a = MatterEntity(composition={"Fe": 1.0}, mass_kg=0.0, internal_energy_j=0.0)
    b = MatterEntity(composition={"H": 1.0}, mass_kg=0.0, internal_energy_j=0.0)
    m = merge([a, b])
    assert m.mass_kg == 0.0
    assert abs(m.composition["Fe"] - 0.5) < 1e-9
    assert abs(m.composition["H"] - 0.5) < 1e-9


def test_m2_10_single_element_entity_at_exact_phase_boundary():
    e = iron_bar(mass=1.0, energy=0.0)
    at_boundary = add_energy(e, e.melt_complete_j_per_kg)
    assert at_boundary.phase == Phase.LIQUID  # >= boundary means the transition is complete


def test_m2_10_fuzz_random_transformation_sequence_conserves_mass_and_energy():
    """`add_energy` is a deliberate external source/sink (heating/cooling a
    sample), so it is exempt from closed-system conservation by design -- only
    split and merge are required to conserve mass/energy internally. This test
    therefore tracks the *declared* external energy injected by every
    add_energy call and asserts the closed-system total only ever changes by
    exactly that much, not by zero. (An earlier version of this test asserted
    the total never changes at all, which is wrong given add_energy's declared
    semantics -- caught by actually running the fuzz sequence rather than
    trusting the assertion looked right.)
    """
    rng = random.Random("hrm-stage2-fuzz-seed")
    kernel = MatterKernel()
    live_ids = [
        kernel.register(MatterEntity(
            composition={"Fe": 0.4, "C": 0.3, "H": 0.3}, mass_kg=100.0, internal_energy_j=20_000.0,
        ))
    ]
    total_mass_start = sum(kernel.get(i).mass_kg for i in live_ids)
    total_energy_start = sum(kernel.get(i).internal_energy_j for i in live_ids)
    external_energy_injected = 0.0

    for _ in range(200):
        action = rng.choice(["split", "merge", "energy"])
        if action == "split" and live_ids:
            target = rng.choice(live_ids)
            n = rng.randint(2, 5)
            weights = [rng.random() + 0.01 for _ in range(n)]
            total = sum(weights)
            ratios = tuple(w / total for w in weights)
            new_ids = kernel.apply_split(target, ratios)
            live_ids.remove(target)
            live_ids.extend(new_ids)
        elif action == "merge" and len(live_ids) >= 2:
            k = rng.randint(2, min(4, len(live_ids)))
            chosen = rng.sample(live_ids, k)
            new_id = kernel.apply_merge(tuple(chosen))
            for c in chosen:
                live_ids.remove(c)
            live_ids.append(new_id)
        elif action == "energy" and live_ids:
            target = rng.choice(live_ids)
            current = kernel.get(target).internal_energy_j
            delta = rng.uniform(-current, current * 2)
            new_id = kernel.apply_add_energy(target, delta)
            external_energy_injected += delta
            live_ids.remove(target)
            live_ids.append(new_id)

    total_mass_end = sum(kernel.get(i).mass_kg for i in live_ids)
    total_energy_end = sum(kernel.get(i).internal_energy_j for i in live_ids)
    assert abs(total_mass_end - total_mass_start) < 1e-4  # mass has no external source in this test
    assert abs((total_energy_end - total_energy_start) - external_energy_injected) < 1e-4


# ---------------------------------------------------------------------------
# Boundary hardening applied proactively (same class of finding as Stage-1 Round 2)
# ---------------------------------------------------------------------------

def test_kernel_port_closures_do_not_resolve_to_a_kernel_object():
    kernel = MatterKernel()
    port = kernel.port()

    def resolves_to_kernel(func, seen=None) -> bool:
        seen = seen or set()
        if id(func) in seen or not hasattr(func, "__code__"):
            return False
        seen.add(id(func))
        for name, cell in zip(func.__code__.co_freevars, func.__closure__ or ()):
            value = cell.cell_contents
            if isinstance(value, MatterKernel):
                return True
            if hasattr(value, "__code__") and resolves_to_kernel(value, seen):
                return True
        return False

    for method_name in ("get", "split", "merge", "add_energy", "state_digest"):
        bound = getattr(port, method_name)
        assert not resolves_to_kernel(bound.__func__), f"port.{method_name} resolves back to a MatterKernel"


def test_m2_7_returned_entity_composition_cannot_mutate_kernel_state():
    """Regression test for a real finding: no reflection needed here at all --
    a plain, ordinary caller of the *legal* `get()` interface could previously
    mutate the dict returned in `.composition` in place and silently corrupt
    the kernel's real internal state, because `frozen=True` on the dataclass
    only blocks reattaching the attribute, not mutating the dict object it
    points to. `composition` is now a `MappingProxyType`, which genuinely
    rejects item assignment.
    """
    kernel = MatterKernel()
    eid = kernel.register(MatterEntity(composition={"Fe": 1.0}, mass_kg=5.0, internal_energy_j=0.0))
    port = kernel.port()
    fetched = port.get(eid)
    with pytest.raises(TypeError):
        fetched.composition["Fe"] = 999.0
    assert port.get(eid).composition["Fe"] == 1.0


def test_checkpoint_round_trip_preserves_state_digest():
    kernel = MatterKernel()
    eid = kernel.register(MatterEntity(composition={"Fe": 0.5, "H": 0.5}, mass_kg=4.0, internal_energy_j=600.0))
    a, b = kernel.apply_split(eid, (0.5, 0.5))
    payload = kernel.checkpoint()
    restored = MatterKernel.from_checkpoint(payload)
    assert restored.state_digest() == kernel.state_digest()
    assert restored.get(a) == kernel.get(a)
    assert restored.get(b) == kernel.get(b)
