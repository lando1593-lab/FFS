import pytest

from ffs.core.units import inches_to_ft_in, parse_dimension_to_inches
from ffs.ingest.scale import parse_scale_text, scale_from_points, verify_with_dimension


@pytest.mark.parametrize(
    "txt, inches",
    [
        ("28'-6\"", 342.0),
        ("28' - 6 1/2\"", 342.5),
        ("12'", 144.0),
        ('6"', 6.0),
        ("30'-0\"", 360.0),
        ('3/4"', 0.75),
        ("1'-0 3/8\"", 12.375),
    ],
)
def test_parse_dimension(txt, inches):
    assert parse_dimension_to_inches(txt) == pytest.approx(inches)


def test_parse_dimension_rejects_junk():
    assert parse_dimension_to_inches("W18X35") is None
    assert parse_dimension_to_inches("") is None
    assert parse_dimension_to_inches("TYP") is None


def test_ft_in_roundtrip():
    assert inches_to_ft_in(342.0) == "28'-6\""
    assert inches_to_ft_in(342.5) == "28'-6 1/2\""
    assert inches_to_ft_in(360.0) == "30'-0\""


@pytest.mark.parametrize(
    "txt, paper_in_per_ft",
    [
        ('1/8" = 1\'-0"', 0.125),
        ('SCALE: 1/4"=1\'-0"', 0.25),
        ('3/16" = 1\'-0"', 0.1875),
        ("1\" = 20'", 0.05),
        ('1 1/2" = 1\'-0"', 1.5),
    ],
)
def test_parse_scale(txt, paper_in_per_ft):
    sc = parse_scale_text(txt)
    assert sc is not None, txt
    assert sc.paper_inches_per_foot == pytest.approx(paper_in_per_ft)


def test_parse_ratio_and_nts():
    sc = parse_scale_text("SCALE 1:100")
    assert sc is not None and sc.label == "1:100"
    assert parse_scale_text("N.T.S.") is None


def test_eighth_scale_math():
    sc = parse_scale_text('1/8" = 1\'-0"')
    # 30 ft at 1/8" scale = 3.75 paper inches = 270 pt
    assert 270 * sc.inches_per_point == pytest.approx(360.0)


def test_calibration_and_verification():
    sc = scale_from_points((0, 0), (270, 0), 360.0)
    ok, err = verify_with_dimension(sc, 270, "30'-0\"")
    assert ok and err < 1e-9
    ok, err = verify_with_dimension(sc, 270, "28'-0\"")
    assert not ok
