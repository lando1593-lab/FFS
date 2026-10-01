"""Synthetic golden → takeoff → persisted members → design assignments → meter / review queue."""

import json

from sqlalchemy import select
from test_thickness_engine import _chart

from ffs.db.assign import (
    assign_designs_for_project,
    ensure_base_scenario,
    open_review_items,
    resolution_meter,
)
from ffs.db.models import DesignAssignment, MemberInstance, Project, session
from ffs.db.store import save_members
from ffs.design.library import DesignLibrary
from ffs.ingest.pdf import load_pdf
from ffs.synth import generate
from ffs.takeoff.pipeline import run_page


def test_takeoff_members_get_design_assignments_and_review_items(tmp_path):
    pdf = generate(tmp_path / "gp0")
    _, members, _ = run_page(load_pdf(pdf)[0])
    assert members
    s = session(f"sqlite:///{tmp_path}/p.sqlite")
    prj = Project(name="gp0")
    s.add(prj)
    s.commit()
    save_members(s, prj, members)
    sections = sorted({m.canonical_section for m in members})
    # a mini library: P723 → S721 chart that prints every section but the first one
    parsed = tmp_path / "parsed"
    for d in ("ul_designs", "charts", "gcp_charts"):
        (parsed / d).mkdir(parents=True)
    rows = [
        ("Unrestrained Beam", sec.replace("X", " x ", 1), sec, 0.5, ["1/2", "5/8", "7/8"])
        for sec in sections[1:]
    ]
    (parsed / "charts" / "p723.json").write_text(
        json.dumps(
            _chart(
                "P723", "Protected Roof Deck", "CAFCO® 400 & ISOLATEK® Type 400", [], xref=["S721"]
            )
        )
    )
    (parsed / "charts" / "s721.json").write_text(
        json.dumps(_chart("S721", "Protected Roof Deck", "CAFCO® 400 & ISOLATEK® Type 400", rows))
    )
    lib = DesignLibrary.load(parsed)
    scn = ensure_base_scenario(s, prj)
    counts = assign_designs_for_project(s, prj, scn, lib, "P723", 1.0, "CAFCO 400", "unrestrained")
    n_missing = sum(1 for m in members if m.canonical_section == sections[0])
    assert counts["unknown"] == n_missing and counts["resolved"] == len(members) - n_missing
    rows_db = list(s.scalars(select(DesignAssignment)))
    assert len(rows_db) == len(members)
    assert all(r.thickness_in == 0.5 for r in rows_db if r.resolution_status == "resolved")
    assert all(r.thickness_source["via"] == "P723 → S721" for r in rows_db if r.thickness_in)
    items = open_review_items(s, prj, scn)
    assert len(items) == n_missing and all(
        it.kind == "unknown" and it.category == "design" for it in items
    )
    assert all("not printed" in it.why for it in items)
    meter = resolution_meter(s, prj, scn)
    assert meter["members"] == len(members) and meter["designs_unresolved"] == n_missing
    assert meter["assigned"]["design"] == len(members) and meter["assigned"]["rating"] == 0
    # every persisted assignment is linked to its member and its assertion
    mids = {m.id for m in s.scalars(select(MemberInstance))}
    assert all(r.member_id in mids and r.assertion_id for r in rows_db)
