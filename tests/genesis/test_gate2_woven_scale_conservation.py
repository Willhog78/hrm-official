"""Physical weaving scale: real source dimensions, finite mass, no fabricated matter.

Only tests existing material functions. Does not confer construction knowledge
or alter the Agentus planner, material model, or deployment configuration.
"""
import math

from hrm_genesis.matter import objects as mo


def _strands(source, number):
    # Use source-table dimensions, a real circular cross-section and independent
    # element inventories. No arbitrary mass injected into a material object.
    spec = mo.FIBER_SOURCES[source]
    length = sum(spec["length_m"]) / 2
    thickness = sum(spec["thickness_mm"]) / 2
    mass = mo.fiber_mass_for(source, length, thickness)
    return [mo.make_fiber(source, {"C": mass}, 0.5, 0.5, f"{source}-{i}")
            for i in range(number)]


def test_interlacing_scale_conserves_constituent_matter():
    for source in ("plant", "bark", "tendon"):
        previous_area = -1.0
        for count in (4, 8, 40, 400):
            fibers = _strands(source, count)
            before = sum(mo.object_mass(s) for s in fibers)
            before_elements = sum(mo.object_elements(s).get("C", 0.0) for s in fibers)
            surface = mo.interlace(fibers, f"woven-{source}-{count}")
            assert surface is not None
            assert len(surface["strands"]) == count
            assert math.isclose(mo.object_mass(surface), before, rel_tol=1e-12)
            assert math.isclose(mo.object_elements(surface)["C"], before_elements, rel_tol=1e-12)
            assert surface["area_m2"] >= 0
            assert surface["area_m2"] <= max(s["length_m"] for s in fibers) ** 2 + 1e-10
            assert surface["area_m2"] >= previous_area
            previous_area = surface["area_m2"]
            print(f"WEAVE_SCALE source={source} strands={count} "
                  f"area_m2={surface['area_m2']:.9f} mass_kg={before:.9f} "
                  f"cohesion={surface['cohesion']:.6f}", flush=True)


def test_four_strands_cannot_make_a_body_scale_sheet():
    for source in ("plant", "bark", "tendon"):
        surface = mo.interlace(_strands(source, 4), f"min-{source}")
        assert surface is not None
        assert surface["area_m2"] < 0.01


if __name__ == "__main__":
    test_interlacing_scale_conserves_constituent_matter()
    test_four_strands_cannot_make_a_body_scale_sheet()
    print("WEAVE_SCALE_COMPLETE", flush=True)
