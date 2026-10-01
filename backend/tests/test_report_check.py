import json

from test_thickness_engine import _chart

from ffs.design.library import DesignLibrary
from ffs.design.report_check import check_drawing_report, conditions_for, product_line, summarize
from ffs.importers.edge_drawing_report import DrawingReport, LegendRow, ReportSheet


def _row(
    desc, label, canon, role, code, design, suffix, tokens, hours, thk, sides=None, extra=None
):
    return LegendRow(
        2,
        desc,
        label,
        canon,
        role,
        sides,
        code,
        design,
        suffix,
        tokens,
        hours,
        f'{thk}"',
        {"1/2": 0.5, "9/16": 0.5625, "7/8": 0.875, "1": 1.0}[thk],
        None,
        extra or {},
    )


def test_code_mapping_is_explicit_and_unmapped_tokens_are_flagged():
    assert product_line("Blaze Shield (Type II)") == "BLAZE-SHIELD II"
    assert product_line("Cafco 400") == "CAFCO 400" and product_line("MK-6 HY") == "MK-6/HY"
    cond, notes = conditions_for(
        _row(
            "x",
            "W 12 X 26",
            "W12X26",
            "primary_beam",
            "N823 NW C",
            "N823",
            None,
            ["NW", "C"],
            1,
            "1/2",
        )
    )
    assert cond == "Cellular or Corrugated Deck Normal Weight" and len(notes) == 2
    cond, notes = conditions_for(
        _row("x", "W 12 X 26", "W12X26", "primary_beam", "P819F B", "P819", "F", ["B"], 1, "1/2")
    )
    assert (
        cond is None
        and any("suffix 'F'" in n for n in notes)
        and any("'B' kept as printed" in n for n in notes)
    )
    cond, notes = conditions_for(
        _row("x", "W 10 X 39", "W10X39", "column", "X790 C", "X790", None, ["C"], 1, "1/2")
    )
    assert cond is None and "wide-flange column chart" in notes[0]


def test_check_rows_verdicts(tmp_path):
    for d in ("ul_designs", "charts", "gcp_charts"):
        (tmp_path / d).mkdir(parents=True)
    charts = [
        _chart(
            "N823",
            "Cellular or Corrugated Deck Normal Weight Concrete",
            "CAFCO® BLAZE-SHIELD® II, HP & ISOLATEK® Type II, HP",
            [
                ("Unrestrained Beam", "W12 x 26", "W12X26", 0.61, ["1/2", "5/8", "7/8"]),
                ("Unrestrained Beam", "W21 x 44", "W21X44", 0.74, ["7/16", "5/8", "7/8"]),
            ],
            date="6/2/2017",
        ),
        _chart(
            "N823",
            "All-Fluted Deck Normal Weight Concrete",
            "CAFCO® BLAZE-SHIELD® II, HP & ISOLATEK® Type II, HP",
            [("Unrestrained Beam", "W12 x 26", "W12X26", 0.61, ["9/16", "5/8", "7/8"])],
            date="6/2/2017",
        ),
    ]
    joist = _chart(
        "N830",
        "Cellular or Corrugated Deck Normal Weight Concrete Joist",
        "CAFCO® BLAZE-SHIELD® II, HP & ISOLATEK® Type II, HP",
        [
            ("Unrestrained Beam", "16K2", None, 5.5, ["7/8", "1", "1-1/8"]),
            ("Unrestrained Beam", "16K4", None, 7.0, ["7/8", "1", "1-1/8"]),
            ("Unrestrained Beam", "18K3", None, 6.6, ["1", "1", "1-1/8"]),
        ],
        date="6/27/2012",
    )
    for r, depth in zip(joist["rows"], (16.0, 16.0, 18.0), strict=True):
        r["depth_in"] = depth
    charts.append(joist)
    for i, c in enumerate(charts):
        (tmp_path / "charts" / f"c{i}.json").write_text(json.dumps(c))
    lib = DesignLibrary.load(tmp_path)
    sheet = ReportSheet(
        2,
        "S121",
        "Calcs Blaze Shield (Type II)",
        "Blaze Shield (Type II)",
        "drawing_report",
        rows=[
            _row(
                "W 12 X 26 - PRIMARY BEAM",
                "W 12 X 26",
                "W12X26",
                "primary_beam",
                "N823 NW C",
                "N823",
                None,
                ["NW", "C"],
                1,
                "1/2",
            ),
            _row(
                "W 21 X 44 - PRIMARY BEAM 4 Sides",
                "W 21 X 44",
                "W21X44",
                "primary_beam",
                "N823 NW C",
                "N823",
                None,
                ["NW", "C"],
                1,
                "1/2",
                sides=4,
            ),
            _row(
                "W 12 X 26 - PRIMARY BEAM",
                "W 12 X 26",
                "W12X26",
                "primary_beam",
                "N823 NW C",
                "N823",
                None,
                ["NW", "C"],
                1,
                "9/16",
            ),
            _row(
                'JOIST 16"',
                'JOIST 16"',
                None,
                "joist",
                "N830 NW C",
                "N830",
                None,
                ["NW", "C"],
                1,
                "7/8",
                extra={"joist_depth_in": 16.0},
            ),
            _row(
                'JOIST 18"',
                'JOIST 18"',
                None,
                "joist",
                "N830 NW C",
                "N830",
                None,
                ["NW", "C"],
                1,
                "7/8",
                extra={"joist_depth_in": 18.0},
            ),
            _row(
                "STEEL DECK TYPE B (1.33 Exp Factor)",
                "STEEL DECK TYPE B (1.33 Exp Factor)",
                None,
                "deck",
                "N823 NW C",
                "N823",
                None,
                ["NW", "C"],
                1,
                "1/2",
            ),
        ],
    )
    rep = DrawingReport("r.pdf", "Fireproofing Drawing Report", "T", "7/31/2023", [sheet])
    checks = check_drawing_report(lib, rep)
    verdicts = [c.verdict for c in checks]
    assert verdicts == ["match", "differs-4-sides", "differs", "match", "differs", "skipped"]
    assert checks[0].query.condition == "Cellular or Corrugated Deck Normal Weight"
    assert (
        checks[0].resolution.selected.source["condition"].startswith("Cellular")
    )  # the AF chart was excluded
    assert checks[0].assumptions == ["restraint assumed unrestrained (not printed on the report)"]
    j16 = checks[3].resolution
    assert j16.status == "resolved" and "2 designations: 16K2, 16K4" in j16.selected.source["row"]
    assert checks[4].resolution.distinct_values() == [1.0]
    assert summarize(checks)["match"] == 2
