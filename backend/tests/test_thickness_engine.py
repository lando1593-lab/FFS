import json
from pathlib import Path

import pytest

from ffs.design.library import DesignLibrary, derived_tube_canonical, rating_hours
from ffs.design.thickness import UNKNOWN, ThicknessQuery, resolve

PARSED = Path(__file__).resolve().parents[2] / "data" / "reference_library" / "parsed"


_SHA: dict = {}


def _sha(*key):
    """A distinct 12-hex 'content hash' per distinct chart (the library dedupes on it)."""
    return _SHA.setdefault(key, f"{len(_SHA):012x}")


def _chart(design, condition, products, rows, date="10/3/2013", xref=None, cols=None, factor="W/D"):
    cols = cols or ["1 Hr", "1-1/2 Hr", "2 Hr"]
    return {
        "source_file": f"isolatek-{design or 'x'}__{_sha(design, condition, products, date)}.pdf",
        "design": design,
        "title_lines": [],
        "condition": condition,
        "products": products,
        "chart_date": date,
        "rating_columns": cols,
        "rating_column_markers": ["", "", ""],
        "factor_kind": factor,
        "rows": [
            {
                "page": 1,
                "section": sec,
                "member_label": label,
                "canonical": canon,
                "family_label": label,
                "wd": wd,
                "metric_label": None,
                "md": None,
                "hp_a": None,
                "thickness_as_printed": vals,
                "thickness_in": [None if v == "NR" else _f(v) for v in vals],
                "not_rated": [v == "NR" for v in vals],
                "metric_member_label": None,
                "depth_in": None,
                "approx_wt": None,
                "rating_columns": None,
            }
            for (sec, label, canon, wd, vals) in rows
        ],
        "notes": [],
        "cross_reference": "Use Design S721 Table" if xref else None,
        "cross_reference_designs": xref or [],
        "footnotes": [],
    }


def _f(s):
    from fractions import Fraction

    if "-" in s:
        w, f = s.split("-")
        return float(w) + float(Fraction(f))
    return float(Fraction(s))


def _ul(design, tables, equations):
    return {
        "agency": "UL",
        "category": "BXUV",
        "design_no": design,
        "design_date": None,
        "last_updated": "2019-10-09",
        "snapshot_date": None,
        "source_url": None,
        "member_category_guess": None,
        "ratings": [],
        "items": [],
        "equations": equations,
        "tables": tables,
        "sfrm_manufacturers": [],
        "reproduction_notice": None,
        "text_sha256": "x",
        "source_file": f"UL_{design}.pdf",
        "unparsed": [],
    }


@pytest.fixture
def lib(tmp_path):
    (tmp_path / "ul_designs").mkdir()
    (tmp_path / "charts").mkdir()
    (tmp_path / "gcp_charts").mkdir()
    # UL X790: a column table with W6x9 and an A/P equation (as printed on the real design)
    x790 = _ul(
        "X790",
        [
            {
                "item_no": "2",
                "kind": "size_wd",
                "headers": [],
                "rating_columns": ["1 Hr", "1-1/2 Hr", "2 Hr"],
                "rating_fields": 0,
                "value_columns": [],
                "condition": "flange columns",
                "units": "in",
                "ratio_names": ["W/D"],
                "notes": [],
                "rows": [
                    {
                        "cells": ["W6x9", "0.33", "15/16", "1-1/4", "1-9/16"],
                        "label": "W6x9",
                        "canonical": "W6X9",
                        "wd": 0.33,
                        "values_in": [0.9375, 1.25, 1.5625],
                        "note": None,
                        "ratios": [0.33],
                        "values": [],
                    }
                ],
            }
        ],
        [
            {
                "item_no": "2B",
                "form": "h = R / (a*(W/D) + b)",
                "a": 188.0,
                "b": 45.0,
                "wd_range": [0.18, 0.49],
                "h_range_in": [0.25, 4.5],
                "as_printed": "R h = 188 (A/P) + 45",
                "factor": "A/P",
                "r_units": "minutes",
                "k": None,
                "c": None,
                "rating": None,
                "rating_hours": None,
                "h_range": [0.25, 4.5],
                "h_units": "in",
                "notes": [],
            }
        ],
    )
    (tmp_path / "ul_designs" / "UL_X790.json").write_text(json.dumps(x790))
    charts = [
        # P723 is a cross-reference page to S721, protected roof deck
        _chart(
            "P723",
            "Protected Roof Deck",
            "CAFCO® 300 Series, CAFCO® 400 & ISOLATEK® Type 300",
            [],
            xref=["S721"],
        ),
        _chart(
            "S721",
            "Protected Roof Deck",
            "CAFCO® 300 Series, CAFCO® 400 & ISOLATEK® Type 300",
            [
                ("Unrestrained Beam", "W12 x 26", "W12X26", 0.61, ["1/2", "5/8", "7/8"]),
                ("Unrestrained Beam", "W6 x 9", "W6X9", 0.33, ["7/8", "1-1/8", "1-1/2"]),
            ],
        ),
        _chart(
            "S721",
            "Protected Roof Deck",
            "CAFCO® 300 Series, CAFCO® 400 & ISOLATEK® Type 300",
            [("Restrained Beam", "W12 x 26", "W12X26", 0.61, ["1/2", "1/2", "3/4"])],
            date="10/3/2013 ",
        ),
        _chart(
            "S721",
            "S721 - Half-Flange Tip Option Protected Roof Deck",
            "CAFCO® 300 Series, CAFCO® 400 & ISOLATEK® Type 300",
            [("Unrestrained Beam", "W12 x 26", "W12X26", 0.61, ["9/16", "3/4", "1"])],
        ),
        _chart(
            "S721",
            "Unprotected Roof Deck",
            "CAFCO® 300 Series, CAFCO® 400 & ISOLATEK® Type 300",
            [("Unrestrained Beam", "W12 x 26", "W12X26", 0.61, ["5/8", "3/4", "1"])],
        ),
        _chart(
            "S721",
            "Protected Roof Deck",
            "CAFCO® FENDOLITE® M-II, TG & ISOLATEK® Type M-II",
            [("Unrestrained Beam", "W12 x 26", "W12X26", 0.61, ["1/2", "5/8", "7/8"])],
            date="10/24/2019",
        ),
        _chart(
            "X790",
            "Structural Steel Square Tube Columns",
            "CAFCO® 300 Series, CAFCO® 400 & ISOLATEK® Type 300",
            [(None, "ST 5 x 5 x 3/8", None, 0.35, ["7/16", "3/4", "1"])],
            factor="A/P",
        ),
        _chart(
            None,
            "Miscellaneous Shapes Single Angles",
            "CAFCO® 300 Series, CAFCO® 400 & ISOLATEK® Type 300",
            [(None, "L3 x 3 x 1/4", "L3X3X1/4", 0.41, ["15/16", "1-1/4", "1-1/2"])],
        ),
    ]
    for i, c in enumerate(charts):
        (tmp_path / "charts" / f"c{i}.json").write_text(json.dumps(c))
    return DesignLibrary.load(tmp_path)


def test_rating_hours_and_derived_tubes():
    assert (
        rating_hours("1-1/2 Hr") == 1.5
        and rating_hours("90 min") == 1.5
        and rating_hours("Rating") is None
    )
    assert derived_tube_canonical("ST 5 x 5 x 3/8") == "HSS5X5X3/8"
    assert derived_tube_canonical("RT 6 x 4 x 1/4") == "HSS6X4X1/4"
    assert derived_tube_canonical("W12 x 26") is None


def test_cross_reference_carries_condition_and_restraint(lib):
    r = resolve(lib, ThicknessQuery("P723", "W12X26", 1.0, "unrestrained", "CAFCO 400"))
    assert r.status == "resolved" and r.value == 0.5
    c = r.selected
    assert c.method == "chart_table" and c.assertion_kind == "FACT" and c.authority == 6
    assert c.source["via"] == "P723 → S721" and c.source["condition"] == "Protected Roof Deck"
    assert c.source["section"] == "Unrestrained Beam" and c.source["application"] == "contour"
    # the restrained table, the half-flange chart and the unprotected-deck chart were excluded
    assert len(r.candidates) == 1
    rr = resolve(lib, ThicknessQuery("P723", "W12X26", 1.5, "restrained", "CAFCO 400"))
    assert rr.value == 0.5 and rr.selected.source["section"] == "Restrained Beam"
    hf = resolve(
        lib,
        ThicknessQuery(
            "P723", "W12X26", 1.0, "unrestrained", "CAFCO 400", application="half_flange_tip"
        ),
    )
    assert hf.value == 0.5625


def test_product_line_is_required_for_a_chart_value(lib):
    r = resolve(lib, ThicknessQuery("P723", "W12X26", 1.0, "unrestrained"))
    assert r.status == "review" and r.value == UNKNOWN
    assert any("no product line given" in x for x in r.reasons)
    assert {c.source["products"][:14] for c in r.candidates} == {"CAFCO® 300 Ser", "CAFCO® FENDOLI"}


def test_ul_table_outranks_chart_and_agreement_resolves(lib):
    r = resolve(lib, ThicknessQuery("X790", "W6X9", 1.0, None, "CAFCO 400"))
    # UL table says 15/16; the S721 chart is for P723 only, so one candidate: the listing
    assert r.status == "resolved" and r.value == 0.9375
    assert r.selected.method == "ul_table" and r.selected.authority == 2
    assert r.selected.source["row"] == "W6x9" and r.selected.source["column"] == "1 Hr"


def test_equation_and_table_routes_conflict_and_both_are_returned(lib):
    r = resolve(lib, ThicknessQuery("X790", "HSS5X5X3/8", 1.0, None, "CAFCO 400"))
    assert r.status == "conflict" and r.value == UNKNOWN
    assert r.distinct_values() == [0.4375, 0.5625]
    eq = next(c for c in r.candidates if c.method == "ul_equation")
    assert eq.assertion_kind == "CALCULATION" and eq.thickness_in == 0.5625
    assert eq.inputs["ratio"] == 0.35 and eq.inputs["R"] == 60.0 and eq.inputs["raw_in"] == 0.5415
    assert "ST 5 x 5 x 3/8" in eq.inputs["ratio_source"]
    tbl = next(c for c in r.candidates if c.method == "chart_table")
    assert tbl.thickness_in == 0.4375 and "derived from the printed label" in tbl.notes[0]


def test_equation_outside_its_range_is_refused(lib):
    r = resolve(
        lib,
        ThicknessQuery(
            "X790",
            "HSS9X9X1/2",
            1.0,
            None,
            "CAFCO 400",
            ratio=0.9,
            ratio_kind="A/P",
            ratio_source="test",
        ),
    )
    assert r.status == "unknown" and any("outside the equation range" in x for x in r.reasons)


def test_shape_chart_is_review_never_resolved(lib):
    r = resolve(lib, ThicknessQuery("P723", "L3X3X1/4", 1.0, "unrestrained", "CAFCO 400"))
    assert r.status == "review" and r.value == UNKNOWN
    assert r.candidates[0].method == "shape_chart" and r.candidates[0].thickness_in == 0.9375
    assert "not tied to design P723" in r.candidates[0].notes[0]


def test_unknown_design_and_unknown_member(lib):
    assert resolve(lib, ThicknessQuery("N999", "W12X26", 1.0)).status == "unknown"
    r = resolve(lib, ThicknessQuery("P723", "W40X503", 1.0, "unrestrained", "CAFCO 400"))
    assert r.status == "unknown" and r.candidates == [] and "not printed" in r.reasons[-1]


@pytest.mark.skipif(not (PARSED / "charts").exists(), reason="parsed reference library not present")
def test_real_library_reproduces_validation_one():
    """docs/validation/2026-10-01: 13 of 13 beams via P723 → S721; HSS both routes; angles."""
    lib = DesignLibrary.load(PARSED)
    beams = {
        "W8X10": 0.625,
        "W10X12": 0.625,
        "W12X14": 0.5625,
        "W12X19": 0.5,
        "W12X26": 0.5,
        "W14X22": 0.5,
        "W14X30": 0.5,
        "W16X26": 0.5,
        "W16X31": 0.5,
        "W16X36": 0.4375,
        "W18X35": 0.5,
        "W18X46": 0.4375,
        "W21X44": 0.4375,
    }
    for m, bid in beams.items():
        r = resolve(lib, ThicknessQuery("P723", m, 1.0, "unrestrained", "CAFCO 400"))
        assert r.status == "resolved" and r.value == bid, (
            m,
            r.status,
            r.distinct_values(),
            r.reasons,
        )
        assert r.selected.source["via"] == "P723 → S721"
    hss = resolve(lib, ThicknessQuery("X790", "HSS5X5X3/8", 1.0, None, "CAFCO 400"))
    assert hss.status == "conflict" and hss.distinct_values() == [0.4375, 0.5625]
    ang = resolve(lib, ThicknessQuery("P723", "L3X3X1/4", 1.0, "unrestrained", "CAFCO 400"))
    assert ang.status == "review" and 0.9375 in ang.distinct_values()
