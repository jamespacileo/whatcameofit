"""The list of sources: each one's licence, credit line and the date its terms were read.

It mirrors `docs/sources.md`, which holds the terms in full. A client sends no request
for a source this list does not hold (`sources.base.require_recorded`), and the export
carries a fact only from a source marked accepted. Behavior: openspec source-clients
and knowledge-cards.
"""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class SourceTerms:
    name: str
    title: str
    licence: str
    # How the source asks to be credited.
    credit: str
    # The source's own front page, for the site's list of data sources.
    home_url: str
    # Where the terms were read, and when.
    terms_url: str
    read_on: date
    # Whether its facts may be published at all.
    accepted: bool
    # Whether its facts may enter the open data file, which is offered under CC BY 4.0.
    in_data_file: bool


_LISTED = (
    SourceTerms(
        name="clinicaltrials.gov",
        title="ClinicalTrials.gov",
        licence="ClinicalTrials.gov terms and conditions",
        credit="ClinicalTrials.gov, U.S. National Library of Medicine",
        home_url="https://clinicaltrials.gov/",
        terms_url="https://clinicaltrials.gov/about-site/terms-conditions",
        read_on=date(2026, 11, 11),
        accepted=True,
        in_data_file=True,
    ),
    SourceTerms(
        name="europepmc",
        title="Europe PMC",
        licence="Europe PMC copyright terms: titles and links only, no abstracts",
        credit="Europe PMC",
        home_url="https://europepmc.org/",
        terms_url="https://europepmc.org/Copyright",
        read_on=date(2026, 11, 11),
        accepted=True,
        in_data_file=True,
    ),
    SourceTerms(
        name="crossref",
        title="Crossref",
        licence="Crossref metadata, almost none of it subject to copyright; no abstracts",
        credit="Crossref",
        home_url="https://www.crossref.org/",
        terms_url="https://www.crossref.org/documentation/retrieve-metadata/rest-api/",
        read_on=date(2026, 11, 11),
        accepted=True,
        in_data_file=True,
    ),
    SourceTerms(
        name="openalex",
        title="OpenAlex",
        licence="CC0 1.0",
        credit="OpenAlex",
        home_url="https://openalex.org/",
        terms_url="https://help.openalex.org/hc/en-us/articles/24397285563671-OpenAlex-data-license",
        read_on=date(2026, 11, 13),
        accepted=True,
        in_data_file=True,
    ),
    SourceTerms(
        name="ror",
        title="Research Organization Registry",
        licence="CC0 1.0",
        credit="Research Organization Registry (ROR)",
        home_url="https://ror.org/",
        terms_url="https://ror.org/terms/",
        read_on=date(2026, 11, 13),
        accepted=True,
        in_data_file=True,
    ),
    SourceTerms(
        name="mesh",
        title="Medical Subject Headings (MeSH)",
        licence="NLM terms and conditions for MeSH data",
        credit="Medical Subject Headings (MeSH), U.S. National Library of Medicine",
        home_url="https://www.nlm.nih.gov/mesh/meshhome.html",
        terms_url="https://www.nlm.nih.gov/databases/download/terms_and_conditions_mesh.html",
        read_on=date(2026, 11, 14),
        accepted=True,
        in_data_file=True,
    ),
    SourceTerms(
        name="gsrs",
        title="Global Substance Registration System (GSRS)",
        licence="CC0 1.0",
        credit="Global Substance Registration System, FDA and NCATS",
        home_url="https://gsrs.ncats.nih.gov/",
        terms_url="https://gsrs.ncats.nih.gov/licensing",
        read_on=date(2026, 11, 14),
        accepted=True,
        in_data_file=True,
    ),
    # Read only to give a brand its ingredient as a name to search the trial registry
    # for. Its terms were read on the date below and the operator has not accepted them,
    # so it is not asked (`cli.resolve.make_brands`): the operator decides whether the
    # terms are accepted and whether and where the statement NLM asks for is shown
    # (docs/sources.md). Nothing from it is published, and it is out of the data file.
    SourceTerms(
        name="rxnorm",
        title="RxNorm, through the RxNav API",
        licence="RxNorm's own content, which NLM states needs no licence; RxNav terms of service",
        # The statement NLM asks an application that uses its data to carry.
        credit=(
            "This product uses publicly available data from the U.S. National Library of"
            " Medicine (NLM), National Institutes of Health, Department of Health and"
            " Human Services; NLM is not responsible for the product and does not endorse"
            " or recommend this or any other product."
        ),
        home_url="https://www.nlm.nih.gov/research/umls/rxnorm/index.html",
        terms_url="https://lhncbc.nlm.nih.gov/RxNav/TermsofService.html",
        read_on=date(2026, 11, 16),
        accepted=False,
        in_data_file=False,
    ),
    # The three below are read for target and drug cards. The operator accepted Open
    # Targets' own data and UniProt's function descriptions for the page and the data
    # file on 2026-11-14 (knowledge-cards, 2a.18; docs/sources.md), and ChEMBL's
    # share-alike facts for drug cards on claim pages, never in the data file, on the
    # same day (knowledge-cards, 6.1; docs/adr/0002).
    SourceTerms(
        name="opentargets",
        title="Open Targets Platform",
        licence="CC0 1.0",
        # The citation the platform asks for (docs/sources.md).
        credit=(
            "Open Targets Platform: Buniello, A. et al. (2025), “Open Targets Platform:"
            " facilitating therapeutic hypotheses building in drug discovery”, Nucleic"
            " Acids Research"
        ),
        home_url="https://platform.opentargets.org/",
        terms_url="https://platform-docs.opentargets.org/licence",
        read_on=date(2026, 11, 14),
        accepted=True,
        in_data_file=True,
    ),
    SourceTerms(
        name="chembl",
        title="ChEMBL, through Open Targets Platform",
        licence="CC BY-SA 3.0 Unported",
        credit="ChEMBL, EMBL-EBI",
        home_url="https://www.ebi.ac.uk/chembl/",
        terms_url="https://chembl.gitbook.io/chembl-interface-documentation/about",
        read_on=date(2026, 11, 14),
        accepted=True,
        # Share-alike, which the data file's licence is not.
        in_data_file=False,
    ),
    SourceTerms(
        name="uniprot",
        title="UniProt, through Open Targets Platform",
        licence="CC BY 4.0",
        credit="UniProt Consortium",
        home_url="https://www.uniprot.org/",
        terms_url="https://www.uniprot.org/help/license",
        read_on=date(2026, 11, 14),
        accepted=True,
        # CC BY 4.0, which the data file's own licence can carry with credit.
        in_data_file=True,
    ),
)

SOURCES: dict[str, SourceTerms] = {listed.name: listed for listed in _LISTED}
