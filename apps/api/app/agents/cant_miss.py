"""Deterministic can't-miss rule table (architecture §3.2 Agent 3, tool ``flag_cant_miss``).

Dangerous, time-critical, commonly-missed diagnoses keyed by presenting-complaint / symptom
keywords. The Sentinel agent forces these onto the differential even at low probability, and
they can never be silently dropped. The rule layer is deterministic so the most safety-critical
scan works partially offline (architecture §9, "rules only"), independent of the LLM.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CantMissRule:
    triggers: tuple[str, ...]
    diagnosis: str
    icd_code: str | None
    why: str


# India-primary-care oriented can't-miss set. Triggers are matched case-insensitively as
# substrings against the presenting complaint + intake answers.
CANT_MISS_RULES: tuple[CantMissRule, ...] = (
    CantMissRule(
        ("chest pain", "chest tightness", "chest discomfort", "left arm", "jaw pain"),
        "Acute coronary syndrome",
        "I21",
        "Time-critical; atypical presentations common in diabetics and women.",
    ),
    CantMissRule(
        ("chest pain", "breathless", "dyspnea", "shortness of breath", "leg swelling", "calf"),
        "Pulmonary embolism",
        "I26",
        "Easily missed; consider with risk factors (immobility, malignancy, post-partum).",
    ),
    CantMissRule(
        ("worst headache", "thunderclap", "sudden headache", "neck stiffness"),
        "Subarachnoid haemorrhage",
        "I60",
        "Sudden severe headache is a red flag until proven otherwise.",
    ),
    CantMissRule(
        ("fever", "neck stiffness", "headache", "photophobia", "rash", "altered"),
        "Bacterial meningitis",
        "G00",
        "Rapidly fatal; low threshold for LP/empiric antibiotics.",
    ),
    CantMissRule(
        ("fever", "travel", "rigors", "chills", "endemic"),
        "Falciparum malaria",
        "B50",
        "Endemic in much of India; severe malaria progresses quickly.",
    ),
    CantMissRule(
        ("fever", "bleeding", "petechiae", "platelet", "dengue", "warning"),
        "Dengue with warning signs",
        "A91",
        "Plasma-leak phase is dangerous; monitor platelets and haematocrit.",
    ),
    CantMissRule(
        ("abdominal pain", "right lower", "rebound", "guarding", "rif"),
        "Acute appendicitis / surgical abdomen",
        "K35",
        "Surgical emergency; perforation risk if delayed.",
    ),
    CantMissRule(
        ("weakness", "face droop", "slurred", "fast", "stroke", "numbness one side"),
        "Acute ischaemic stroke",
        "I63",
        "Thrombolysis window is narrow; time is brain.",
    ),
    CantMissRule(
        ("breathless", "wheeze", "unable to speak", "silent chest", "asthma"),
        "Life-threatening asthma exacerbation",
        "J46",
        "Silent chest / exhaustion signals imminent respiratory failure.",
    ),
    CantMissRule(
        ("polyuria", "polydipsia", "vomiting", "abdominal pain", "ketones", "diabetes"),
        "Diabetic ketoacidosis",
        "E10.1",
        "Can present as abdominal pain; check ketones and pH.",
    ),
    CantMissRule(
        ("fever", "confusion", "low blood pressure", "tachycardia", "sepsis", "hypotension"),
        "Sepsis / septic shock",
        "A41",
        "Hour-1 bundle saves lives; screen with qSOFA.",
    ),
    CantMissRule(
        ("pregnan", "abdominal pain", "bleeding", "amenorrhea", "missed period"),
        "Ectopic pregnancy",
        "O00",
        "Rupture is life-threatening; test βhCG in any woman of childbearing age.",
    ),
)


def match_cant_miss(text: str) -> list[CantMissRule]:
    """Return can't-miss rules whose triggers appear in ``text`` (deterministic)."""
    haystack = (text or "").lower()
    hits: list[CantMissRule] = []
    for rule in CANT_MISS_RULES:
        matched = sum(1 for t in rule.triggers if t in haystack)
        # Require ≥2 trigger hits for multi-symptom syndromes, 1 for highly specific ones.
        threshold = 2 if len(rule.triggers) >= 4 else 1
        if matched >= threshold:
            hits.append(rule)
    return hits
