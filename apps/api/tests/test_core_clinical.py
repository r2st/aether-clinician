"""Unit tests for deterministic clinical computations (eGFR, age)."""

from __future__ import annotations

from datetime import date

import pytest

from app.core.clinical import (
    age_from_dob,
    ckd_epi_2021_egfr,
    egfr_reference_abnormal,
    is_creatinine_marker,
)


def test_age_from_dob():
    assert age_from_dob(date(1980, 6, 15), date(2026, 6, 14)) == 45
    assert age_from_dob(date(1980, 6, 15), date(2026, 6, 15)) == 46


def test_ckd_epi_normal_male():
    # Healthy 45y male, creatinine 0.9 -> eGFR comfortably > 90.
    result = ckd_epi_2021_egfr(creatinine_mg_dl=0.9, age_years=45, sex="male")
    assert result.formula_name == "CKD-EPI_2021"
    assert result.value > 90
    assert result.inputs["sex"] == "male"


def test_ckd_epi_impaired():
    # Elevated creatinine 2.5 in a 70y male -> markedly reduced eGFR.
    result = ckd_epi_2021_egfr(creatinine_mg_dl=2.5, age_years=70, sex="male")
    assert result.value < 30
    assert egfr_reference_abnormal(result.value)


def test_ckd_epi_female_adjustment():
    male = ckd_epi_2021_egfr(creatinine_mg_dl=1.0, age_years=50, sex="male")
    female = ckd_epi_2021_egfr(creatinine_mg_dl=1.0, age_years=50, sex="female")
    # Same creatinine: the female equation yields a lower eGFR (lower k, factor).
    assert female.value < male.value


def test_ckd_epi_rejects_bad_input():
    with pytest.raises(ValueError):
        ckd_epi_2021_egfr(creatinine_mg_dl=0, age_years=40, sex="male")
    with pytest.raises(ValueError):
        ckd_epi_2021_egfr(creatinine_mg_dl=1.0, age_years=0, sex="male")


@pytest.mark.parametrize(
    "name,expected",
    [
        ("Creatinine", True),
        ("Serum Creatinine", True),
        ("S. Creatinine", True),
        ("HbA1c", False),
        ("Hemoglobin", False),
    ],
)
def test_creatinine_marker_detection(name, expected):
    assert is_creatinine_marker(name) is expected
