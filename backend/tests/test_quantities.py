import pytest

from ffs.design.quantities import (
    aggregate,
    member_quantity,
    nominal_weight_plf,
    perimeter_from_dimensions,
    surface_basis,
)
from ffs.steel.aisc import ShapeDatabase


def test_perimeter_formulas_and_weights():
    # W12X26: d 12.22, bf 6.49, tw 0.23
    assert perimeter_from_dimensions(12.22, 6.49, 0.23, 4) == (
        pytest.approx(49.94),
        "4-sided contour",
    )
    assert perimeter_from_dimensions(12.22, 6.49, 0.23, 3) == (
        pytest.approx(43.45),
        "3-sided contour",
    )
    assert perimeter_from_dimensions(12.22, 6.49, 0.23, 4, "box") == (
        pytest.approx(37.42),
        "4-sided box",
    )
    assert perimeter_from_dimensions(12.22, 6.49, 0.23, 3, "box") == (
        pytest.approx(30.93),
        "3-sided box",
    )
    assert nominal_weight_plf("W12X26") == 26 and nominal_weight_plf("C8X11.5") == 11.5
    assert nominal_weight_plf("HSS5X5X3/8") is None and nominal_weight_plf("L3X3X1/4") is None


def test_chart_wd_route_matches_the_manufacturer_workbook():
    """Isolatek's estimating workbook prints 3.54 sq ft/lf for W12X26 beams (W/D 0.61) and
    4.08 for columns (W/D 0.53): exactly W / (W/D) / 12."""
    beam = surface_basis(
        "W12X26",
        3,
        {
            "document": "s721.pdf",
            "design": "S721",
            "section": "Unrestrained Beam",
            "condition": "Protected Roof Deck",
            "row": "W12 x 26",
        },
        {"ratio": 0.61, "ratio_kind": "W/D"},
    )
    assert beam.method == "chart_wd" and beam.basis == "3-sided contour (beam chart)"
    assert beam.sf_per_lf == pytest.approx(3.55, abs=0.01) and beam.inputs["weight_plf"] == 26
    assert beam.source["row"] == "W12 x 26" and "two decimals" in beam.notes[0]
    col = surface_basis(
        "W12X26",
        4,
        {
            "document": "x790.pdf",
            "design": "X790",
            "condition": "Wide Flange Structural Steel Columns",
            "row": "W12 x 26",
        },
        {"ratio": 0.53, "ratio_kind": "W/D"},
    )
    assert col.basis == "4-sided contour (column chart)" and col.sf_per_lf == pytest.approx(
        4.09, abs=0.01
    )


def test_aisc_dimensions_outrank_the_chart(tmp_path):
    csv = tmp_path / "aisc.csv"
    csv.write_text("AISC_Manual_Label,Type,W,d,bf,tw,tf,A\nW12X26,W,26,12.2,6.49,0.23,0.38,7.65\n")
    db = ShapeDatabase.load(csv)
    b = surface_basis(
        "W12X26", 3, {"design": "S721"}, {"ratio": 0.61, "ratio_kind": "W/D"}, aisc=db
    )
    assert b.method == "aisc_dimensions" and b.basis == "3-sided contour"
    assert b.perimeter_in == pytest.approx(2 * 12.2 + 3 * 6.49 - 2 * 0.23)
    assert b.source == {"document": "aisc.csv", "label": "W12X26"}


def test_geometry_routes_and_unknowns():
    hss = surface_basis("HSS5X5X3/8", 4, None, None)
    assert (
        hss.method == "nominal_geometry"
        and hss.perimeter_in == 20
        and hss.sf_per_lf == pytest.approx(20 / 12)
    )
    assert surface_basis("HSS6X4X1/4", 3, None, None).perimeter_in == 6 + 8
    rnd = surface_basis("HSS6X1/4", 4, None, None)
    assert rnd.basis == "round outside perimeter" and rnd.perimeter_in == pytest.approx(
        18.85, abs=0.01
    )
    ang = surface_basis("L3X3X1/4", 3, None, None)
    assert ang.perimeter_in == pytest.approx(11.5)
    assert surface_basis("W12X26", 3, None, None) is None  # no AISC, no chart ratio: unknown
    assert (
        surface_basis("W12X26", 3, {"design": "S721"}, {"ratio": 0.35, "ratio_kind": "A/P"}) is None
    )
    wb = surface_basis(
        "W12X26",
        3,
        None,
        None,
        workbook_sf={"W12X26": (3.54, {"document": "WB4.xlsm", "basis": "roof beam"})},
    )
    assert wb.method == "workbook_sf" and wb.sf_per_lf == 3.54


def test_member_quantities_and_aggregation():
    src = {
        "document": "s721.pdf",
        "design": "S721",
        "section": "Unrestrained Beam",
        "condition": "Protected Roof Deck",
        "row": "W12 x 26",
    }
    inp = {"ratio": 0.61, "ratio_kind": "W/D"}
    r1 = member_quantity("m1", "W12X26", "L2", "beam", 240.0, 0.5, "P723", "CAFCO 400", src, inp)
    assert r1.status == "ok" and r1.sides == 3 and r1.sides_source == "assumed"
    assert r1.length_ft == 20 and r1.sq_ft == pytest.approx(20 * 26 / 0.61 / 12, abs=0.01)
    assert r1.bd_ft == pytest.approx(r1.sq_ft * 0.5, abs=0.01)
    assert any("ASSUMPTION" in n for n in r1.notes)
    r2 = member_quantity("m2", "W12X26", "L2", "beam", None, 0.5, "P723", "CAFCO 400", src, inp)
    r3 = member_quantity("m3", "W12X26", "L2", "beam", 120.0, None, "P723", "CAFCO 400", src, inp)
    r4 = member_quantity("m4", "16K2", "L2", "joist", 300.0, 0.75, "P723", "CAFCO 400", {}, {})
    r5 = member_quantity(
        "m5",
        "HSS5X5X3/8",
        "L1",
        "column",
        144.0,
        0.5625,
        "X790",
        "CAFCO 400",
        {},
        {},
        sides=4,
        sides_source="condition_assignment",
    )
    assert (r2.status, r3.status, r4.status) == ("no_length", "no_thickness", "no_surface_basis")
    assert r5.sq_ft == pytest.approx(20 / 12 * 12) and r5.sides_source == "condition_assignment"
    qs = aggregate(
        [r1, r2, r3, r4, r5],
        "scn",
        waste_pct=10,
        waste_source="company estimating guide 2024 p3",
        yield_bdft_per_bag=40,
        yield_source="CAFCO 400 C-TDS 10-20",
    )
    t = qs.totals
    assert t["members"] == 5 and t["members_quantified"] == 2 and qs.unresolved == 3
    assert t["bd_ft_theoretical"] == pytest.approx(r1.bd_ft + r5.bd_ft, abs=0.1)
    assert t["bd_ft_adjusted"] == pytest.approx(t["bd_ft_theoretical"] * 1.1, abs=0.1)
    assert t["bags"] == -(-t["bd_ft_adjusted"] // 40)  # ceil
    assert "P723 | CAFCO 400 | 0.5 in | 3 sides" in qs.by_condition
    assert qs.by_level["L1"]["members"] == 1 and qs.by_level["L2"]["members"] == 1
    qs0 = aggregate([r1], "scn")
    assert (
        qs0.totals["bd_ft_adjusted"] is None and qs0.totals["bags"] is None
    )  # no waste, no yield: no numbers
