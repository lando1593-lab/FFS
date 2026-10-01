import pytest

from ffs.steel.designation import ShapeFamily, find_designations, parse_designation


@pytest.mark.parametrize(
    "raw, canonical, family",
    [
        ("W18x35", "W18X35", ShapeFamily.W),
        ("W 18 X 35", "W18X35", ShapeFamily.W),
        ("W18×35", "W18X35", ShapeFamily.W),
        ("W-18x35", "W18X35", ShapeFamily.W),
        ("W8x10", "W8X10", ShapeFamily.W),
        ("W14x90", "W14X90", ShapeFamily.W),
        ("HP14x73", "HP14X73", ShapeFamily.HP),
        ("C10x15.3", "C10X15.3", ShapeFamily.C),
        ("MC12x31", "MC12X31", ShapeFamily.MC),
        ("WT9x25", "WT9X25", ShapeFamily.WT),
        ("HSS6x6x1/4", "HSS6X6X1/4", ShapeFamily.HSS_RECT),
        ("HSS 8x4x3/8", "HSS8X4X3/8", ShapeFamily.HSS_RECT),
        ("HSS6.000x0.250", "HSS6.000X0.250", ShapeFamily.HSS_ROUND),
        ("HSS6x.250", "HSS6X0.250", ShapeFamily.HSS_ROUND),
        ("L4x4x1/2", "L4X4X1/2", ShapeFamily.L),
        ("L3-1/2x3-1/2x1/4", "L3-1/2X3-1/2X1/4", ShapeFamily.L),
        ("2L4x4x1/2", "2L4X4X1/2", ShapeFamily.DOUBLE_L),
        ("PIPE 4 STD", "PIPE4STD", ShapeFamily.PIPE),
        ("24K7", "24K7", ShapeFamily.JOIST),
        ("36LH12", "36LH12", ShapeFamily.JOIST),
        ("48G8N10K", "48G8N10K", ShapeFamily.JOIST_GIRDER),
    ],
)
def test_canonical(raw, canonical, family):
    pd = parse_designation(raw)
    assert pd is not None, raw
    assert pd.canonical == canonical
    assert pd.family == family
    assert pd.confidence >= 0.7


def test_ocr_repair_lowers_confidence_and_records_note():
    pd = parse_designation("WI8x3S")
    assert pd is not None
    assert pd.canonical == "W18X35"
    assert pd.confidence <= 0.6
    assert any("OCR" in n for n in pd.notes)


def test_distinct_shapes_never_merge():
    a = parse_designation("W18x35")
    b = parse_designation("W18x36")
    assert a.canonical != b.canonical


def test_status_prefix():
    pd = parse_designation("(E) W12x26")
    assert pd is not None and pd.prefix == "E"
    pd = parse_designation("(D)W10x22")
    assert pd is not None and pd.prefix == "D"


def test_find_multiple_in_note():
    res = find_designations("NOTES: ALL LINTELS W8X10 TYP. KICKERS L3X3X1/4 @ 4'-0\" O.C.")
    assert [r.canonical for r in res] == ["W8X10", "L3X3X1/4"]


def test_implausible_flagged():
    pd = parse_designation("W99x5000")
    assert pd is not None
    assert pd.confidence <= 0.3


def test_not_a_designation():
    assert parse_designation("WIDTH 18") is None
    assert find_designations("SEE 3/S-501") == []
    assert find_designations("MAX 5x5 OPENING") == []
