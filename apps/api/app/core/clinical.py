"""Deterministic clinical computations (no LLM, offline-safe).

These power DerivedMarker computation and renal-dosing safety checks. All formulas are
versioned for reproducibility per the audit-trail requirement.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class EgfrResult:
    value: float  # mL/min/1.73m^2
    formula_name: str
    formula_version: str
    inputs: dict


def age_from_dob(dob: date, on: date) -> int:
    years = on.year - dob.year - ((on.month, on.day) < (dob.month, dob.day))
    return years


def ckd_epi_2021_egfr(*, creatinine_mg_dl: float, age_years: int, sex: str) -> EgfrResult:
    """CKD-EPI 2021 creatinine equation (race-free).

    eGFR = 142 * min(Scr/k, 1)^a * max(Scr/k, 1)^-1.200 * 0.9938^age * (1.012 if female).
    k = 0.7 (female) / 0.9 (male); a = -0.241 (female) / -0.302 (male).
    """
    if creatinine_mg_dl <= 0:
        raise ValueError("creatinine must be positive")
    if age_years <= 0:
        raise ValueError("age must be positive")

    is_female = sex.lower().startswith("f")
    k = 0.7 if is_female else 0.9
    a = -0.241 if is_female else -0.302
    scr_k = creatinine_mg_dl / k

    egfr = 142.0 * (min(scr_k, 1.0) ** a) * (max(scr_k, 1.0) ** -1.200) * (0.9938**age_years)
    if is_female:
        egfr *= 1.012

    return EgfrResult(
        value=round(egfr, 2),
        formula_name="CKD-EPI_2021",
        formula_version="2021",
        inputs={
            "creatinine_mg_dl": creatinine_mg_dl,
            "age_years": age_years,
            "sex": "female" if is_female else "male",
        },
    )


def egfr_reference_abnormal(egfr_value: float) -> bool:
    """eGFR < 90 mL/min/1.73m^2 is below the normal reference floor."""
    return egfr_value < 90.0


# Common creatinine marker name aliases seen in Indian lab reports.
CREATININE_ALIASES = (
    "creatinine",
    "serum creatinine",
    "s. creatinine",
    "s creatinine",
    "creat",
)


def is_creatinine_marker(marker_name: str) -> bool:
    name = marker_name.strip().lower()
    return any(alias in name for alias in CREATININE_ALIASES)
