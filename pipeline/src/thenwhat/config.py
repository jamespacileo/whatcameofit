"""Settings read from the environment. Nothing here has a secret default."""

from datetime import date
from decimal import Decimal
from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class SourceAllowance(BaseModel):
    """How many requests a source may receive in a period, and how far apart."""

    requests: int
    period_hours: float
    interval_seconds: float
    # How long to stop asking after the source says "too many requests" without
    # saying for how long.
    pause_minutes: float = 60


# At or below what each source publishes (docs/sources.md). SOURCE_ALLOWANCES in the
# environment replaces or adds entries by source name.
DEFAULT_ALLOWANCES = {
    "clinicaltrials.gov": SourceAllowance(requests=5000, period_hours=24, interval_seconds=0.5),
    "mediacloud": SourceAllowance(requests=4000, period_hours=168, interval_seconds=30),
    # The page reader is the operator's own machine (openspec page-reading). This is a
    # ceiling on how hard the pipeline drives it; how often each site is asked is the
    # reader's to decide.
    "reader": SourceAllowance(requests=3000, period_hours=24, interval_seconds=1),
    # NCBI allows three requests a second without a key; this is two (docs/sources.md).
    "pubmed": SourceAllowance(requests=5000, period_hours=24, interval_seconds=0.5),
    # NCBI asks that a job of more than 100 requests runs off-peak. Requests sent in its
    # peak hours are counted here as well, across processes and runs; the client stops
    # at the hundredth until the hours pass or the day's count is restored.
    "pubmed-peak-hours": SourceAllowance(requests=100, period_hours=24, interval_seconds=0),
}


class Settings(BaseSettings):
    # Empty variables, as in a freshly copied .env, count as not set.
    model_config = SettingsConfigDict(extra="ignore", env_ignore_empty=True)

    database_url: str
    # Sent in the User-Agent of every registry request. No request is sent without it.
    contact_email: str | None = None

    # The page reader (openspec page-reading, ADR 0005 and 0006): the address the
    # pipeline asks it at and its key. No default: no page is read while either is empty.
    firecrawl_api_url: str | None = None
    firecrawl_api_key: str | None = None
    # How many requests the pipeline has with the reader at once, across its threads.
    # The machine takes at most 4 and is shared with other projects.
    reader_reads_at_once: int = Field(default=2, ge=1, le=4)
    # How long one request to the reader may take.
    reader_timeout_seconds: float = 120

    # OpenAlex's free key, for the literature search. Empty turns paper search off and
    # leaves the rest of resolution as it is.
    openalex_api_key: str | None = None

    # Language model: provider and model as "provider:model". No default on purpose.
    llm_model: str | None = None
    llm_monthly_budget_usd: Decimal = Decimal("13")
    llm_input_usd_per_mtok: Decimal | None = None
    llm_output_usd_per_mtok: Decimal | None = None

    # Which backend answers bounded decisions: "llm" or "openai-decisions".
    decision_backend: str = "llm"
    # For "openai-decisions": the model by the provider's own name (when empty, the
    # model of LLM_MODEL if that is an OpenAI one) and its price per million input tokens.
    decisions_model: str | None = None
    decisions_input_usd_per_mtok: Decimal | None = None

    review_confidence_threshold: float = 0.95
    # An evidence-stage reading the threshold above did not confirm is still exported,
    # marked as unconfirmed, when the stage it chose has at least this probability
    # (openspec review, ADR 0004). It never sets the stage or the status. A value above 1
    # exports none.
    stage_show_above: float = 0.5
    # A new candidate match scored under this is rejected by rule instead of waiting
    # for review. It is kept and can be listed and approved. 0 turns the rule off.
    match_reject_below: float = 0.05
    # A new trial candidate scored for the claim's indication at or above this is
    # approved by rule and published. The default is where the site's "High match" band
    # starts. 0 turns the rule off (openspec auto-publish).
    # A related paper scored at or above it is approved by rule too (openspec
    # related-research), and one scored under `match_reject_below` is rejected.
    match_accept_above: float = 0.8
    # How many candidate subject terms are kept for a claim (openspec knowledge-cards).
    term_candidates_max: int = 10
    # How many genes named in a claim's intervention are kept as candidate targets.
    target_candidates_max: int = 3
    # Reported statements (openspec reported-statements). A statement the statement check
    # gives this probability or more that its article says it is approved by rule and
    # published; one below it waits, unpublished. 0 turns the rule off.
    statement_accept_above: float = 0.8
    # The most reported statements kept for one article.
    statements_per_article: int = 6
    # A proposed statement sharing this many consecutive words with its article is
    # refused as copied.
    statement_copied_run: int = 8
    # Record readings (openspec claim-at-a-glance, ADR 0003). A reading the model gives
    # less confidence than this is not exported, so the page and the data file give the
    # registry's own words for that answer instead. 0 exports every reading the rule kept.
    reading_accept_above: float = 0.8
    # How many trials the readings step asks the model about at a time. The monthly
    # spend ceiling is looked at before each group, so a run can pass it by the cost of
    # one group's calls at most. 1 asks about one trial at a time.
    readings_at_once: int = Field(default=6, ge=1, le=16)
    # Decide new drafts by rule: approved, and published, when the intervention is a
    # name; rejected and kept otherwise. On by default: approval needs no person
    # (openspec auto-publish).
    approve_drafts_by_rule: bool = True
    no_signal_years: int = 3
    # A stored paper record older than this is asked for again at fetch; a younger one
    # causes no request (openspec paper-facts).
    paper_record_max_age_days: int = 30

    # Backfill (openspec work-ledger, source-allowances, article-leads).
    # JSON by source name, for example
    # {"mediacloud": {"requests": 4000, "period_hours": 168, "interval_seconds": 30}}.
    source_allowances: dict[str, SourceAllowance] = {}
    # A record that failed this many times is skipped and reported.
    backfill_attempt_limit: int = 3
    # A record put off for one reason for longer than this is said to need a fix, so it
    # is listed and not asked for without end.
    work_put_off_days: int = 30
    # Media Cloud key, and the collections and single outlets to search, as
    # comma-separated ids from its directory. The news search refuses to run while the
    # key is empty or while neither list names anything.
    mediacloud_api_key: str | None = None
    mediacloud_collection_ids: str = ""
    mediacloud_source_ids: str = ""
    # At most this many article leads are kept for one trial.
    leads_per_trial: int = 20
    # PubMed, through NCBI's E-utilities (docs/sources.md). The name every request gives
    # for this software, with no spaces, and the key the operator made in an NCBI
    # account. A step that asks PubMed refuses while the tool name or CONTACT_EMAIL is
    # empty; the key is optional and only raises NCBI's own limit.
    pubmed_tool: str = "thenwhat"
    pubmed_api_key: str | None = None
    # How many trials' numbers one PubMed search carries.
    pubmed_trials_per_request: int = Field(default=50, ge=1, le=200)

    # Link leads (openspec link-leads). The Reddit communities whose submissions are
    # loaded, separated by commas, without "r/". A Reddit load refuses while it is empty.
    link_lead_subreddits: str = ""

    # At most this many stored claims and registry trials are linked to one link lead
    # by screening (openspec lead-screening).
    lead_links_max: int = 10

    # Triage (openspec lead-triage): a link lead scored at or above the first is passed
    # and may be read; one scored below the second is rejected and kept; between them it
    # is held. No default on purpose: the operator sets both from the evaluation report,
    # and until then nothing is passed.
    lead_pass_above: float | None = None
    lead_reject_below: float | None = None

    # Evaluation (openspec lead-evaluation): no link lead is read until this many leads
    # carry a person's label and a score from the current version of triage.
    lead_evaluation_min_labels: int = 200

    # Reading (openspec lead-reading). A new claim's vertical is chosen by a decision and
    # accepted only at or above this probability; below it no claim is made.
    vertical_accept_above: float = 0.8
    # An article whose treatment shares a name with existing claims joins the likeliest
    # of them when the same-claim decision gives at least this probability to the
    # article reporting one of them (one minus what it gives "none of these"), and gives
    # that claim more than half. Otherwise a new claim is drafted.
    same_claim_accept_above: float = 0.6
    # An article becomes a claim, or joins one, only when a decision on the read's own
    # headline and summary gives at least this probability to its being about one
    # treatment for one condition, whether the treatment is new or long established.
    # Below it no claim is made and the lead says so.
    treatment_accept_above: float = 0.5
    # A lead for a claim that already has this many source articles is held, unless it
    # was shared before the claim's first reported date.
    lead_reads_per_claim: int = 3
    # The least time between two pages asked of one outlet in a run of reads. A lead
    # whose outlet was asked more recently is left for a later run, and the run goes on
    # with other outlets. Whether a site may be asked is the page reader's decision;
    # this only keeps the pipeline from sending it one outlet's pages back to back.
    # 0 turns it off.
    reader_outlet_gap_seconds: float = Field(default=30, ge=0)
    # A lead whose site answered that it is busy, throttling or failing is asked for
    # again after this many hours.
    lead_site_retry_hours: float = Field(default=6, gt=0)
    # Read only leads first shared on or after this day. Unset reads leads of any date.
    # It narrows a run to a period; a lead outside it stays due for a later run.
    lead_read_since: date | None = None
    # The named set of stored trials being worked (openspec trial-report-links), such as
    # active-since-2025. While it is set, a held lead with an exact or strong link to a
    # trial of the set is read, and leads so linked are read before the others, phase 3
    # first. Unset, no set orders the reading.
    lead_read_trial_set: str | None = None
    # The share of the month's ceiling that reads for a set of trials may use
    # (`thenwhat backfill read-set`), in US dollars. Decided by the operator on
    # 2026-11-17.
    trial_route_monthly_usd: Decimal = Decimal("15")
    # Score only leads first shared on or after this day. Unset scores leads of any date.
    # An older lead stays unscored, and so unread, until a later run widens the period.
    lead_triage_since: date | None = None

    # Measurements (openspec processing-metrics). The folder single-step measurements
    # are written to; empty turns measuring off. No default on purpose: they are large
    # and belong on a disk the operator chooses.
    measure_dir: Path | None = None
    # Who is writing them: this device's name in reports.
    measure_writer: str = "pipeline"
    # How many days single-step measurements are kept before only totals remain, and
    # how many for those of readers' lookups. No defaults: measuring refuses to start
    # without them.
    measure_keep_days: int | None = Field(default=None, ge=1)
    measure_lookup_keep_days: int | None = Field(default=None, ge=1)

    def chosen_subreddits(self) -> frozenset[str]:
        return frozenset(
            name.strip().removeprefix("r/")
            for name in self.link_lead_subreddits.split(",")
            if name.strip()
        )

    def allowances(self) -> dict[str, SourceAllowance]:
        return {**DEFAULT_ALLOWANCES, **self.source_allowances}


def load_settings() -> Settings:
    return Settings()
