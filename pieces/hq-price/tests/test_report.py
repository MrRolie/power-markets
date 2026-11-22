import pytest

from hq_price import report


def test_missing_number_refuses():
    rec = {"run_id": "r1", "label": "validation (seen)", "results": {"T1_da_lbmp": {"scores": {"B0": {"mae": 1.0}}}}}
    with pytest.raises(report.Untraceable):
        report.scores_table(rec, "T1_da_lbmp", "en")


def test_null_number_refuses():
    with pytest.raises(report.Untraceable):
        report.get({"run_id": "r", "a": None}, "a")


def test_french_number_format():
    assert report.f2(1234.5, "fr") == "1\u202f234,50" and report.f2(-0.001, "fr") == "0,00"
    assert report.pct(0.9, "fr") == "90,0\u202f%"
