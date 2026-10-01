"""Tests for tools/lacie_inventory/inventory.py (loaded by path; it is a standalone script)."""

import importlib.util
import json
import os
import sys
from pathlib import Path

import pymupdf
import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "tools" / "lacie_inventory" / "inventory.py"
spec = importlib.util.spec_from_file_location("lacie_inventory", SCRIPT)
inv = importlib.util.module_from_spec(spec)
sys.modules["lacie_inventory"] = inv
spec.loader.exec_module(inv)


def _pdf(path: Path, text: str, encrypt: bool = False) -> None:
    d = pymupdf.open()
    p = d.new_page()
    p.insert_textbox(pymupdf.Rect(36, 36, 576, 756), text, fontsize=9)
    if encrypt:
        d.save(path, encryption=pymupdf.PDF_ENCRYPT_AES_256, owner_pw="o", user_pw="u")
    else:
        d.save(path)
    d.close()


@pytest.fixture
def lib(tmp_path):
    root = tmp_path / "lib"
    (root / "Projects" / "2014 Job").mkdir(parents=True)
    _pdf(
        root / "Projects" / "2014 Job" / "spray chart.pdf",
        "ISOLATEK CAFCO 300 SPRAY CHART 2 HR UL DESIGN N708 W12X26 Design No. X772 Project: Mercy Hospital 3/14/2014",
    )
    _pdf(root / "encrypted.pdf", "secret", encrypt=True)
    (root / "zero.pdf").write_bytes(b"")
    (root / "corrupt.pdf").write_bytes(b"%PDF-1.4 garbage")
    (root / "old.xls").write_bytes(b"\xd0\xcf\x11\xe0" + b"\0" * 100)
    (root / "notes.txt").write_text(
        "Carboline Pyrocrete 241 - 1-1/2 hr rating, see S-201 and ASTM E119, 2000 psi\n"
    )
    os.symlink(root, root / "Projects" / "loop")
    return root


def _run(root: Path, out: Path, **kw) -> inv.Catalog:
    cat = inv.Catalog(out, root)
    try:
        inv.inventory(root, cat, kw.get("max_files"), 16, 4, 600, False)
    finally:
        cat.close()
    inv.write_outputs(cat)
    return cat


def test_walk_records_errors_and_continues(lib, tmp_path):
    cat = _run(lib, tmp_path / "out")
    rows = {e.rel_path: e for e in cat.entries}
    assert "encrypted.pdf" in rows and "encrypted" in rows["encrypted.pdf"].error
    assert rows["zero.pdf"].error == "zero-byte file"
    assert rows["corrupt.pdf"].error
    assert "legacy" in rows["old.xls"].error
    assert any(
        "not followed" in (e.error or "") for e in cat.entries
    )  # symlink loop recorded, not walked
    assert len([e for e in cat.entries if e.file_class != "directory"]) == 6
    # streaming jsonl has every row
    lines = (tmp_path / "out" / "catalog.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == len(cat.entries)
    assert (tmp_path / "out" / "summary.md").exists() and (
        tmp_path / "out" / "summary_paths.md"
    ).exists()
    # csv has a BOM for Excel
    assert (tmp_path / "out" / "catalog.csv").read_bytes().startswith(b"\xef\xbb\xbf")
    summary = (tmp_path / "out" / "summary.md").read_text(encoding="utf-8")
    assert "spray chart.pdf" not in summary  # counts only


def test_classification_signals(lib, tmp_path):
    cat = _run(lib, tmp_path / "out")
    rows = {e.rel_path: e for e in cat.entries}
    sc = rows[str(Path("Projects") / "2014 Job" / "spray chart.pdf")]
    assert sc.doc_type == "spray_chart", sc.doc_type_scores
    assert sc.manufacturer == "isolatek"
    assert "2 HR" in sc.ratings
    assert set(sc.ul_designs) == {"N708", "X772"}  # strict: "UL DESIGN N708" and "Design No. X772"
    assert "W12X26" in sc.member_terms
    assert 2014 in sc.years_seen and "3/14/2014" in sc.dates_seen
    assert sc.project_hint and sc.project_hint.startswith("Mercy Hospital")
    notes = rows["notes.txt"]
    assert notes.manufacturer == "carboline"
    assert "1-1/2 HR" in notes.ratings and "2 HR" not in notes.ratings
    assert "S201" not in notes.ul_designs  # a sheet number is not a strict design reference
    assert 2000 not in notes.years_seen  # "2000 psi" is not a year


def test_bad_mtime_does_not_abort(lib, tmp_path):
    assert inv.iso_mtime(1e20) == ""
    assert inv.iso_mtime(-11644473600) in ("", inv.iso_mtime(-11644473600))  # must not raise
    assert inv.iso_mtime(0)  # epoch is fine


def test_unreadable_directory_recorded(lib, tmp_path):
    if os.geteuid() == 0:
        pytest.skip("root bypasses permissions")
    bad = lib / "locked"
    bad.mkdir()
    bad.chmod(0)
    try:
        cat = _run(lib, tmp_path / "out")
        assert cat.dirs_failed == 1
        assert any("DIR UNREADABLE" in (e.error or "") for e in cat.entries)
    finally:
        bad.chmod(0o755)


def test_interrupt_writes_partial(lib, tmp_path, monkeypatch):
    calls = {"n": 0}
    orig = inv.classify

    def boom(e, text):
        calls["n"] += 1
        if calls["n"] == 2:
            raise KeyboardInterrupt
        orig(e, text)

    monkeypatch.setattr(inv, "classify", boom)
    cat = inv.Catalog(tmp_path / "out", lib)
    try:
        inv.inventory(lib, cat, None, 16, 4, 600, False)
    finally:
        cat.close()
    assert cat.interrupted
    inv.write_outputs(cat)
    assert "PARTIAL" in (tmp_path / "out" / "summary.md").read_text(encoding="utf-8")


def test_guard_refuses_out_inside_or_same_volume(lib, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["inventory.py", str(lib), "--out", str(lib / "out")])
    assert inv.main() == 2
    assert "inside the library root" in capsys.readouterr().err
    monkeypatch.setattr(
        sys, "argv", ["inventory.py", str(lib), "--out", str(tmp_path / "elsewhere")]
    )
    rc = inv.main()  # same volume as tmp root → refused unless allowed
    assert rc == 2
    assert "same volume" in capsys.readouterr().err
    monkeypatch.setattr(
        sys,
        "argv",
        ["inventory.py", str(lib), "--out", str(tmp_path / "elsewhere"), "--allow-same-volume"],
    )
    assert inv.main() == 0
    assert (tmp_path / "elsewhere" / "summary.md").exists()


def test_undecodable_filename_survives(tmp_path):
    if sys.platform == "win32":
        pytest.skip("posix-only byte filenames")
    root = tmp_path / "lib"
    root.mkdir()
    bad = os.path.join(os.fsencode(root), b"caf\xe9.txt")
    with open(bad, "wb") as f:
        f.write(b"hello")
    cat = _run(root, tmp_path / "out")
    inv.write_outputs(cat)
    rows = json.loads(
        (tmp_path / "out" / "catalog.jsonl").read_text(encoding="utf-8").splitlines()[0]
    )
    assert rows["filename"].startswith("caf")


def test_media_counted_not_opened_and_exclude(tmp_path):
    root = tmp_path / "lib"
    (root / "Christmas 2019").mkdir(parents=True)
    (root / "Work").mkdir()
    (root / "Christmas 2019" / "IMG_0001.jpg").write_bytes(b"\xff\xd8garbage")
    (root / "Christmas 2019" / "clip.mov").write_bytes(b"\0" * 100)
    (root / "Work" / "site photo.jpg").write_bytes(b"\xff\xd8garbage")
    (root / "Work" / "notes.txt").write_text("cafco 2 hr")
    cat = inv.Catalog(tmp_path / "out", root, media_mode="count")
    try:
        inv.inventory(root, cat, None, 16, 4, 600, False)
    finally:
        cat.close()
    inv.write_outputs(cat)
    assert [e.filename for e in cat.entries] == ["notes.txt"]
    assert cat.media["Christmas 2019"]["files"] == 2 and cat.media["Christmas 2019"]["video"] == 1
    assert cat.media["Work"]["image"] == 1
    summary = (tmp_path / "out" / "summary.md").read_text(encoding="utf-8")
    assert "files: 3" in summary and "Christmas" not in summary
    assert "Christmas 2019" in (tmp_path / "out" / "summary_paths.md").read_text(encoding="utf-8")
    # exclude skips the folder entirely; list mode records media by name without hashing
    cat2 = inv.Catalog(tmp_path / "out2", root, media_mode="list", excludes=["christmas*"])
    try:
        inv.inventory(root, cat2, None, 16, 4, 600, False)
    finally:
        cat2.close()
    names = sorted(e.filename for e in cat2.entries)
    assert names == ["notes.txt", "site photo.jpg"]
    photo = next(e for e in cat2.entries if e.filename == "site photo.jpg")
    assert photo.sha256 is None and photo.doc_type == "media" and photo.snippet == ""
    assert len(cat2.excluded_dirs) == 1
