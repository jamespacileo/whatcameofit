"""The shape a language model must return for one news article."""

from typing import Annotated, Literal

from pydantic import BaseModel, Field

ShortText = Annotated[str, Field(min_length=1, max_length=200)]


class NamedEntity(BaseModel):
    type: Literal["person", "institution", "company"]
    name: ShortText


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
        max_length=3,
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
        default_factory=list, description="People, institutions and companies named."
    )
    promises: list[Annotated[str, Field(min_length=1, max_length=300)]] = Field(
        default_factory=list,
        description="Each timeline the article promises, as a short phrase. Empty if none.",
    )
