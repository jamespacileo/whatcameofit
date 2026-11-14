"""The name a registry trial is searched by. Cases are the registry fields of the 200
phase 3 trials sampled on 2026-11-14 (docs/research/phase3-article-hit-rate).
Scenario names are from openspec article-leads."""

import json
import re
from pathlib import Path

import pytest

from thenwhat.backfill.trial_names import indication_words, name_under_test

SAMPLE = json.loads(
    (
        Path(__file__).parent / "fixtures" / "clinicaltrials" / "phase3_sample_trials.json"
    ).read_text()
)
BY_ID = {trial["nct"]: trial for trial in SAMPLE}


@pytest.mark.parametrize(
    ("nct", "name"),
    [
        # A plain name, and the first of several products.
        ("NCT01305655", "Glucarpidase"),
        ("NCT00281918", "Rituximab"),
        # Dose, form and route are dropped. Scenario: Dose and form in the registry name
        ("NCT06904261", "Migalastat HCl"),
        ("NCT01997268", "SC401B"),
        ("NCT03213639", "Esomeprazole"),
        ("NCT00703781", "bromfenac"),
        ("NCT03942419", "Atropine"),
        ("NCT04948333", "ABL001"),
        # A placebo listed first is passed over.
        ("NCT00464269", "Brivaracetam"),
        ("NCT02402530", "Neridronic acid"),
        # A combination is searched by its first product.
        ("NCT00650689", "Ezetimibe"),
        ("NCT00084240", "Azithromycin"),
        # Brackets go; a code name is a name.
        ("NCT00696631", "Dronedarone"),
        ("NCT06970743", "BGB-16673"),
        # A name too short to search falls back to the registry's other name.
        ("NCT01451203", "CDP870"),
    ],
)
def test_the_name_is_the_intervention_under_test_alone(nct: str, name: str):
    assert name_under_test(BY_ID[nct]["interventions"]) == name


@pytest.mark.parametrize(
    "nct",
    [
        # Scenario: Only a placebo or a description
        "NCT03275922",  # a three-letter code and its placebo
        "NCT07284394",  # a way of giving chemotherapy
        "NCT03001960",  # the timing of a procedure
        "NCT00097708",  # "experimental anti-anxiety drug"
        "NCT07276542",  # a dosing plan
        "NCT05967130",  # a kind of product
    ],
)
def test_a_trial_with_no_usable_name_has_none(nct: str):
    assert name_under_test(BY_ID[nct]["interventions"]) is None


def test_placebos_and_devices_alone_give_no_name():
    assert name_under_test([{"type": "DRUG", "name": "Placebo"}]) is None
    assert name_under_test([{"type": "DEVICE", "name": "Stentrode"}]) is None
    assert name_under_test([]) is None


def test_most_sampled_trials_get_a_name_and_no_name_carries_a_dose_or_a_control():
    names = [name_under_test(trial["interventions"]) for trial in SAMPLE]
    found = [name for name in names if name]

    assert len(found) >= 185
    for name in found:
        assert not re.search(r"placebo|\d\s*(mg|ml|%)", name, re.IGNORECASE), name
        assert len(name.split()) <= 3 and len(name) >= 4, name


@pytest.mark.parametrize(
    ("conditions", "words"),
    [
        (["Early Alzheimer's Disease"], "alzheimer"),
        (["Relapsing Multiple Sclerosis"], "sclerosis"),
        (["Acute Lymphoblastic Leukemia (ALL)"], "lymphoblastic leukemia"),
        (["Diabetes Mellitus, Type 2"], "diabetes"),
        # The first condition with a telling word is used.
        (["Pain", "Infant, Newborn"], "infant newborn"),
        (["Cancer"], None),
        ([], None),
    ],
)
def test_the_indication_is_the_conditions_telling_words(conditions: list[str], words: str | None):
    assert indication_words(conditions) == words
