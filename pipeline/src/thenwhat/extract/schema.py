"""The shape a language model must return for one news article."""

from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator

from thenwhat.domain import StatementBasis, StatementFirmness, StatementKind, StatementSpeaker

ShortText = Annotated[str, Field(min_length=1, max_length=200)]
# The most search phrases a treatment is given or kept.
MAX_SEARCH_PHRASES = 3


class NamedEntity(BaseModel):
    type: Literal["person", "institution", "company"]
    name: ShortText


class ProposedStatement(BaseModel):
    """A reported statement as the model proposes it, before it is checked. The length
    limit is a refusal rule, not a validation, so one long statement does not cost the
    whole draft."""

    text: str = Field(
        min_length=1,
        description=(
            "What the article says, in one sentence of your own words, under 200"
            " characters. Not who said it, which is the speaker. No quotation marks, no"
            " names of people."
        ),
    )
    kind: StatementKind = Field(
        description=(
            "effect: what it did or does; safety: harms or side effects; how_it_works;"
            " who_it_could_help; comparison: against an existing treatment;"
            " what_it_could_lead_to."
        )
    )
    firmness: StatementFirmness = Field(
        description="fact when the article states it as fact; possibility otherwise."
    )
    speaker: StatementSpeaker = Field(
        description=(
            "Who the article has saying it: article (the article itself), researcher,"
            " company, patient or other_expert."
        )
    )
    basis: StatementBasis = Field(
        description=(
            "What the article says it rests on: people (a study in people), animals,"
            " laboratory (cells or laboratory work) or not_said."
        )
    )


STATEMENTS_DESCRIPTION = (
    "What the article says about the intervention beyond its timeline, most important"
    " first. Empty if it says nothing more."
)


class StatementsDraft(BaseModel):
    """The statements of an article read again for statements only."""

    statements: list[ProposedStatement] = Field(
        default_factory=list, description=STATEMENTS_DESCRIPTION
    )


class Draft(BaseModel):
    headline: ShortText = Field(description="What was claimed, in one neutral line.")
    summary: str = Field(
        min_length=1,
        max_length=500,
        description="Your own words. Never copy sentences from the article.",
    )
    intervention: ShortText = Field(
        description="The drug, device or method, by its name alone: no maker or mechanism."
    )
    intervention_synonyms: list[ShortText] = Field(
        default_factory=list,
        description=(
            "Other names the article gives it: a brand name, a code such as ABC-123, or a"
            " generic name. Never a description such as 'the drug', 'the pill' or"
            " 'a one-time treatment'. Empty if the article gives no other name."
        ),
    )
    intervention_search_phrases: list[ShortText] = Field(
        default_factory=list,
        max_length=MAX_SEARCH_PHRASES,
        description=(
            "Up to three short phrases a clinical trial registry or a paper would use for"
            " this treatment when the article gives it no product name, most specific first,"
            " for example 'median nerve stimulation'. Never a bare word such as 'the device'."
            " Empty when the names above are enough."
        ),
    )
    indication: ShortText = Field(description="The condition it is claimed to treat.")
    paper_title: ShortText | None = Field(
        default=None, description="Title of the scientific paper reported on, if named."
    )
    paper_doi: str | None = Field(
        default=None,
        pattern=r"^10\.\d{4,9}/\S+$",
        description="DOI of that paper, only if the article gives it.",
    )
    entities: list[NamedEntity] = Field(
        default_factory=list,
        description=(
            "Institutions and companies named, and each person the article names as"
            " carrying out or leading the research, by full name. Never a patient, a"
            " relative, a reporter or someone only commenting."
        ),
    )
    promises: list[Annotated[str, Field(min_length=1, max_length=300)]] = Field(
        default_factory=list,
        description="Each timeline the article promises, as a short phrase. Empty if none.",
    )
    statements: list[ProposedStatement] = Field(
        default_factory=list, description=STATEMENTS_DESCRIPTION
    )

    @field_validator("entities")
    @classmethod
    def _people_have_full_names(cls, entities: list[NamedEntity]) -> list[NamedEntity]:
        """A person given by one name is dropped: a report names a patient, often a
        child, by first name, and a researcher by full name."""
        return [e for e in entities if e.type != "person" or len(e.name.split()) > 1]
