"""The kinds of intervention a claim's can be given, each tied to one MeSH descriptor.
Behavior: openspec knowledge-cards, "An intervention with no exact term is given its
kind". Pure: no database, network, clock or model.

A kind is added or removed by editing the list. The label is NLM's own for the
descriptor on the day the list was checked (2026-11-14) and is only shown to the
decision; a card's label and definition come from the term's stored record.
"""

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

# The kind chosen for the claim's intervention.
KIND_CHOSEN = "kind_chosen"
# The registry lists the intervention, by an equal name, with this type in this many of
# the claim's approved trials.
REGISTRY_LISTS_TYPE = "registry_lists_type"
KIND_REASON_CODES = (KIND_CHOSEN, REGISTRY_LISTS_TYPE)


@dataclass(frozen=True, slots=True)
class Kind:
    code: str
    # The MeSH descriptor whose record is the kind's card.
    identifier: str
    label: str


KINDS: tuple[Kind, ...] = (
    Kind("drug", "D004364", "Pharmaceutical Preparations"),
    Kind("antibody", "D000911", "Antibodies, Monoclonal"),
    Kind("peptide", "D010455", "Peptides"),
    Kind("oligonucleotide", "D009841", "Oligonucleotides"),
    Kind("messenger_rna", "D012333", "RNA, Messenger"),
    Kind("vaccine", "D014612", "Vaccines"),
    Kind("gene_therapy", "D015316", "Genetic Therapy"),
    Kind("gene_editing", "D000072669", "Gene Editing"),
    Kind("cell_therapy", "D064987", "Cell- and Tissue-Based Therapy"),
    Kind("stem_cell_transplant", "D033581", "Stem Cell Transplantation"),
    Kind("transplant", "D014180", "Transplantation"),
    Kind("tissue_engineering", "D023822", "Tissue Engineering"),
    Kind("biomaterial", "D001672", "Biocompatible Materials"),
    Kind("device", "D004864", "Equipment and Supplies"),
    Kind("implant", "D019736", "Prostheses and Implants"),
    Kind("electrical_stimulation", "D004599", "Electric Stimulation Therapy"),
    Kind("surgical_procedure", "D013514", "Surgical Procedures, Operative"),
    Kind("radiotherapy", "D011878", "Radiotherapy"),
    Kind("phage_therapy", "D000071059", "Phage Therapy"),
    Kind("probiotic", "D019936", "Probiotics"),
    Kind("diet", "D004035", "Diet Therapy"),
    Kind("dietary_supplement", "D019587", "Dietary Supplements"),
    Kind("exercise", "D005081", "Exercise Therapy"),
)


def _same(one: str, other: str) -> bool:
    return " ".join(one.split()).casefold() == " ".join(other.split()).casefold()


def registry_types(
    trial_payloads: Iterable[Mapping[str, Any]], names: Sequence[str]
) -> list[dict[str, Any]]:
    """The registry's type for the claim's intervention, as reasons: for each type, the
    number of the claim's approved trials that list an intervention under it whose name
    equals one of `names`, most trials first.

    `trial_payloads` are the stored records of the claim's approved trials; a trial
    stored with several of its events counts once. An intervention under another name,
    such as a comparator or a drug given alongside, is not read.
    """
    trials: dict[str, Mapping[str, Any]] = {}
    for payload in trial_payloads:
        section = payload.get("protocolSection")
        if not isinstance(section, Mapping):
            continue
        identification = section.get("identificationModule")
        number = identification.get("nctId") if isinstance(identification, Mapping) else None
        if isinstance(number, str) and number:
            trials[number] = section  # the record stored last is the latest

    counts: dict[str, int] = {}
    for section in trials.values():
        arms = section.get("armsInterventionsModule")
        listed = arms.get("interventions") if isinstance(arms, Mapping) else None
        types: set[str] = set()
        for entry in listed if isinstance(listed, Sequence) else []:
            if not isinstance(entry, Mapping):
                continue
            name, kind = entry.get("name"), entry.get("type")
            if (
                isinstance(name, str)
                and isinstance(kind, str)
                and kind
                and any(_same(name, own) for own in names if own.strip())
            ):
                types.add(kind)
        for kind in types:
            counts[kind] = counts.get(kind, 0) + 1
    return [
        {"code": REGISTRY_LISTS_TYPE, "type": kind, "trials": count}
        for kind, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    ]
