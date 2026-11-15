"""Measuring triage on labelled link leads. Scenario names are from openspec
lead-evaluation. Every lead here is synthetic."""

from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from thenwhat.backfill.link_evaluation import (
    BadLabelFile,
    UnknownLabel,
    UnknownLead,
    evaluate,
    label_lead,
    label_leads,
    labels_at_version,
    reading_refusal,
    sample_leads,
    spot_check,
    tenth_of,
)
from thenwhat.db.models import LinkLead, LinkLeadLabel, LinkShare
from thenwhat.domain import Decider, LeadVerdict, OutletKind, ScreenOutcome
from thenwhat.export.build import build_export

NOW = datetime(2026, 11, 20, 9, 0, tzinfo=UTC)
WHEN = datetime(2019, 5, 4, 10, 30, tzinfo=UTC)
REPORT = LeadVerdict.TREATMENT_REPORT.value
OTHER = LeadVerdict.HEALTH_OTHER.value


def lead(
    session: Session,
    number: int,
    score: float | None,
    *,
    platform: str = "hackernews",
    version: int | None = 1,
) -> LinkLead:
    record = LinkLead(
        url=f"https://www.bbc.com/news/health-{number}",
        url_key=f"bbc.com/news/health-{number}",
        outlet="bbc.com",
        outlet_kind=OutletKind.GENERAL_NEWS,
        title=f"A synthetic headline {number}",
        first_shared_at=WHEN,
        screen_outcome=ScreenOutcome.IN_SCOPE,
        triage_score=score,
        triage_version=version if score is not None else None,
    )
    session.add(record)
    session.flush()
    session.add(
        LinkShare(
            link_lead_id=record.id,
            platform=platform,
            community=platform,
            shared_at=WHEN,
            score=1,
            item_number=number if platform == "hackernews" else None,
        )
    )
    session.flush()
    return record


def spread(session: Session, per_tenth: int, *, platform: str = "hackernews") -> list[LinkLead]:
    """Leads with scores in the middle of every tenth: per_tenth in each."""
    made = []
    for tenth in range(10):
        for place in range(per_tenth):
            number = len(session.scalars(select(LinkLead.id)).all())
            made.append(lead(session, number, tenth / 10 + 0.05, platform=platform))
            assert place >= 0
    return made


def label(session: Session, record: LinkLead, value: str, by: Decider = Decider.HUMAN) -> None:
    label_lead(session, record.id, value, by=by, now=NOW)


# --- sampling ----------------------------------------------------------------------


def test_a_sample_takes_equal_numbers_from_each_tenth_and_shows_no_score(session: Session):
    """Scenario: A sample of 200"""
    spread(session, 25)

    sample = sample_leads(session, size=200, seed="1", version=1)

    assert (len(sample.leads), sample.per_tenth, sample.short) == (200, 20, {})
    ids = [one.lead_id for one in sample.leads]
    scores = session.scalars(select(LinkLead.triage_score).where(LinkLead.id.in_(ids)))
    chosen = {tenth_of(score or 0.0) for score in scores}
    assert chosen == set(range(10))
    assert not hasattr(sample.leads[0], "score")
    assert sample.leads[0].title.startswith("A synthetic headline")


def test_a_samples_order_does_not_give_away_the_scores(session: Session):
    """Scenario: A sample of 200. Found on the first real run: the sample was listed
    lowest tenth first, so a lead's place told its score."""
    spread(session, 25)

    sample = sample_leads(session, size=200, seed="1", version=1)

    ids = [one.lead_id for one in sample.leads]
    scores = dict(session.execute(select(LinkLead.id, LinkLead.triage_score)).all())
    tenths = [tenth_of(scores[lead_id] or 0.0) for lead_id in ids]
    assert tenths != sorted(tenths)
    # No run of the first twenty is one tenth.
    assert len(set(tenths[:20])) > 3


def test_a_sample_can_be_drawn_from_one_tenth(session: Session):
    """Scenario: A crowded tenth"""
    spread(session, 40)

    sample = sample_leads(session, size=30, seed="1", version=1, only_tenth=0)

    ids = [one.lead_id for one in sample.leads]
    scores = session.scalars(select(LinkLead.triage_score).where(LinkLead.id.in_(ids))).all()
    assert len(ids) == 30 and all(tenth_of(score or 0.0) == 0 for score in scores)


def test_a_thin_tenth_gives_what_it_has_and_is_reported_short(session: Session):
    """Scenario: A thin tenth"""
    for number in range(30):
        lead(session, number, 0.05)
    for number in range(30, 35):
        lead(session, number, 0.95)

    sample = sample_leads(session, size=200, seed="1", version=1)

    assert len(sample.leads) == 25
    assert sample.short[9] == 5 and sample.short[5] == 0 and 0 not in sample.short


def test_the_same_seed_draws_the_same_sample_and_another_seed_another(session: Session):
    spread(session, 30)

    first = sample_leads(session, size=100, seed="a", version=1)
    again = sample_leads(session, size=100, seed="a", version=1)
    other = sample_leads(session, size=100, seed="b", version=1)

    assert [one.lead_id for one in first.leads] == [one.lead_id for one in again.leads]
    assert [one.lead_id for one in first.leads] != [one.lead_id for one in other.leads]


def test_leads_that_are_labelled_are_left_out_of_a_sample(session: Session):
    """Scenario: A lead an assistant has labelled"""
    leads = spread(session, 2)
    label(session, leads[0], REPORT)
    label(session, leads[1], REPORT, Decider.ASSISTANT)

    sample = sample_leads(session, size=20, seed="1", version=1)

    drawn = {one.lead_id for one in sample.leads}
    # A lead anyone has labelled is not drawn again.
    assert leads[0].id not in drawn and leads[1].id not in drawn


def test_a_sample_is_spread_across_platforms(session: Session):
    for number in range(10):
        lead(session, number, 0.55, platform="hackernews")
    for number in range(10, 20):
        lead(session, number, 0.55, platform="reddit")

    sample = sample_leads(session, size=40, seed="1", version=1)

    platforms = [
        session.scalars(
            select(LinkShare.platform).where(LinkShare.link_lead_id == one.lead_id)
        ).one()
        for one in sample.leads
    ]
    assert (platforms.count("hackernews"), platforms.count("reddit")) == (2, 2)


# --- labels ------------------------------------------------------------------------


def test_a_person_s_label_and_an_assistant_s_are_kept_apart(session: Session):
    """Scenarios: The operator labels a lead, An assistant labels a lead"""
    record = lead(session, 1, 0.9)

    label(session, record, REPORT)
    label(session, record, OTHER, Decider.ASSISTANT)
    label(session, record, OTHER)  # a second label from a person replaces the first

    labels = {
        row.labelled_by: row.label
        for row in session.scalars(
            select(LinkLeadLabel).where(LinkLeadLabel.link_lead_id == record.id)
        )
    }
    assert labels == {
        Decider.HUMAN: LeadVerdict.HEALTH_OTHER,
        Decider.ASSISTANT: LeadVerdict.HEALTH_OTHER,
    }


def test_a_label_that_is_not_an_option_is_refused(session: Session):
    """Scenario: A label that is not an option"""
    record = lead(session, 1, 0.9)

    with pytest.raises(UnknownLabel, match="treatment_report, health_other, not_health"):
        label(session, record, "breakthrough")
    with pytest.raises(UnknownLead):
        label_lead(session, 999_999_999, REPORT, by=Decider.HUMAN, now=NOW)
    assert session.scalars(select(LinkLeadLabel)).all() == []


# --- the report --------------------------------------------------------------------


def test_each_tenth_counts_by_how_many_scored_leads_it_holds(session: Session):
    """Scenarios: After 200 labels, A crowded low tenth"""
    low = [lead(session, number, 0.05) for number in range(60)]
    high = [lead(session, 100 + number, 0.95) for number in range(20)]
    # Two labelled in each tenth: one of the low pair reports a treatment, both high do.
    label(session, low[0], REPORT)
    label(session, low[1], OTHER)
    label(session, high[0], REPORT)
    label(session, high[1], REPORT)

    figures = evaluate(session, version=1).overall

    assert (figures.labels, figures.labels_by_tenth[0], figures.labels_by_tenth[9]) == (4, 2, 2)
    # A low label stands for 30 leads and a high one for 10: 30 reports low, 20 high.
    at_half = next(row for row in figures.rows if row.threshold == 0.5)
    assert at_half.precision == pytest.approx(1.0)
    assert at_half.recall == pytest.approx(20 / 50)
    assert at_half.passed == 20
    at_tenth = next(row for row in figures.rows if row.threshold == 0.1)
    assert at_tenth.passed == 20
    assert figures.unlabelled_tenths == []


def test_a_tenth_with_scored_leads_and_no_label_is_named(session: Session):
    lead(session, 1, 0.05)
    record = lead(session, 2, 0.95)
    label(session, record, REPORT)

    figures = evaluate(session, version=1).overall

    assert figures.unlabelled_tenths == [0]


def test_figures_are_given_for_each_platform(session: Session):
    """Scenario: Two platforms"""
    on_hn = lead(session, 1, 0.95, platform="hackernews")
    on_reddit = lead(session, 2, 0.95, platform="reddit")
    label(session, on_hn, REPORT)
    label(session, on_reddit, OTHER)

    evaluation = evaluate(session, version=1)

    def precision(platform: str) -> float | None:
        rows = evaluation.by_platform[platform].rows
        return next(row for row in rows if row.threshold == 0.9).precision

    assert (precision("hackernews"), precision("reddit")) == (1.0, 0.0)
    assert evaluation.overall.labels == 2


def test_an_assistant_s_label_counts_where_no_person_has_labelled(session: Session):
    """Scenarios: Only an assistant has labelled a lead, Both have labelled a lead,
    Labels by an assistant and spot-checks by the operator"""
    leads = [lead(session, number, 0.95) for number in range(4)]
    for one in leads:
        label(session, one, REPORT, Decider.ASSISTANT)

    by_assistant = evaluate(session, version=1)

    assert (by_assistant.overall.labels, by_assistant.by_assistant, by_assistant.by_person) == (
        4,
        4,
        0,
    )
    assert by_assistant.overall.rows[-1].precision == pytest.approx(1.0)

    # The operator checks two of them, agreeing with one and correcting the other.
    label(session, leads[0], REPORT)
    label(session, leads[1], OTHER)
    checked = evaluate(session, version=1)

    assert (checked.overall.labels, checked.by_assistant, checked.by_person) == (4, 2, 2)
    assert (checked.checked, checked.agreed) == (2, 1)
    # The corrected lead counts as the operator labelled it: three of four are reports.
    assert checked.overall.rows[-1].precision == pytest.approx(0.75)


def test_the_strongest_disagreements_are_listed(session: Session):
    wrong_high = lead(session, 1, 0.97)
    right = lead(session, 2, 0.93)
    label(session, wrong_high, OTHER)
    label(session, right, REPORT)

    evaluation = evaluate(session, version=1)

    assert [case.lead_id for case in evaluation.disagreements] == [wrong_high.id]


def test_with_no_label_there_are_no_figures(session: Session):
    """Scenario: No labels yet"""
    lead(session, 1, 0.95)

    figures = evaluate(session, version=1).overall

    assert figures.labels == 0
    assert all(row.precision is None and row.recall is None for row in figures.rows)


# --- the gate ----------------------------------------------------------------------


def refusal(
    session: Session,
    *,
    version: int = 1,
    min_labels: int = 3,
    pass_above: float | None = 0.7,
    reject_below: float | None = 0.2,
) -> str | None:
    return reading_refusal(
        session,
        version=version,
        min_labels=min_labels,
        pass_above=pass_above,
        reject_below=reject_below,
    )


def test_too_few_labels_keep_leads_from_being_read(session: Session):
    """Scenario: Too few labels"""
    for number in range(2):
        label(session, lead(session, number, 0.9), REPORT)
    label(session, lead(session, 9, 0.9), REPORT, Decider.ASSISTANT)

    message = refusal(session, min_labels=200)

    # An assistant's label counts towards the number, by the operator's decision.
    assert message is not None and "197 more are needed" in message


def test_an_unset_threshold_keeps_leads_from_being_read(session: Session):
    for number in range(3):
        label(session, lead(session, number, 0.9), REPORT)

    assert "LEAD_PASS_ABOVE is not set" in (refusal(session, pass_above=None) or "")
    both = refusal(session, pass_above=None, reject_below=None) or ""
    assert "LEAD_PASS_ABOVE and LEAD_REJECT_BELOW are not set" in both
    assert refusal(session) is None


def test_labels_count_again_once_their_leads_are_scored_at_a_new_version(session: Session):
    """Scenario: Triage version raised"""
    leads = [lead(session, number, 0.9) for number in range(3)]
    for record in leads:
        label(session, record, REPORT)

    assert labels_at_version(session, 2) == 0
    assert "3 more are needed" in (refusal(session, version=2) or "")

    for record in leads:  # triage runs again at version 2
        record.triage_version = 2
    session.flush()

    assert labels_at_version(session, 2) == 3
    assert refusal(session, version=2) is None


def test_the_export_is_the_same_before_and_after_labelling(session: Session):
    """Scenario: Export after labelling"""
    record = lead(session, 1, 0.9)
    before = build_export(session, now=NOW).model_dump_json()

    label(session, record, REPORT)

    assert build_export(session, now=NOW).model_dump_json() == before


# --- labels from a file ------------------------------------------------------------


def test_a_file_of_labels_is_recorded_as_an_assistant_s(session: Session):
    """Scenario: A file of 200 labels"""
    leads = [lead(session, number, 0.5) for number in range(3)]
    lines = [
        "# a comment, and a blank line follow",
        "",
        f"{leads[0].id}\ttreatment_report",
        f"{leads[1].id}, health_other",
        f"{leads[2].id} not_health",
    ]

    number = label_leads(session, lines, by=Decider.ASSISTANT, now=NOW)

    labels = {
        row.link_lead_id: (row.label, row.labelled_by)
        for row in session.scalars(select(LinkLeadLabel))
    }
    assert number == 3
    assert labels[leads[0].id] == (LeadVerdict.TREATMENT_REPORT, Decider.ASSISTANT)
    assert labels[leads[2].id] == (LeadVerdict.NOT_HEALTH, Decider.ASSISTANT)


@pytest.mark.parametrize(
    ("bad", "said"),
    [
        ("{id} breakthrough", "Line 2 is not a lead's number and a label"),
        ("{id}", "Line 2 is not a lead's number and a label"),
        ("999999999 not_health", "Line 2 names the link lead 999999999"),
    ],
)
def test_one_bad_line_fails_the_whole_file_and_is_named(session: Session, bad: str, said: str):
    """Scenario: One bad line"""
    first, second = lead(session, 1, 0.5), lead(session, 2, 0.5)
    lines = [f"{first.id} treatment_report", bad.format(id=second.id)]

    with pytest.raises(BadLabelFile, match=said):
        label_leads(session, lines, by=Decider.HUMAN, now=NOW)
    assert session.scalars(select(LinkLeadLabel)).all() == []


# --- the operator's spot-check -------------------------------------------------------


def test_the_spot_check_lists_disagreements_and_a_random_draw_without_scores(session: Session):
    """Scenarios: After an assistant has labelled a sample, The operator corrects a label"""
    agreeing = [lead(session, number, 0.95) for number in range(40)]
    apart = [lead(session, 100 + number, 0.05) for number in range(3)]
    for one in [*agreeing, *apart]:
        label(session, one, REPORT, Decider.ASSISTANT)
    by_person = lead(session, 200, 0.05)
    label(session, by_person, REPORT)

    found = spot_check(session, version=1, seed="1")
    again = spot_check(session, version=1, seed="1")
    other = spot_check(session, version=1, seed="2")

    assert {one.lead_id for one in found.disagreements} == {one.id for one in apart}
    assert len(found.random) == 30
    assert {one.lead_id for one in found.random} <= {one.id for one in agreeing}
    assert found.random == again.random and found.random != other.random
    assert found.disagreements[0].assistants_label is LeadVerdict.TREATMENT_REPORT
    assert not hasattr(found.random[0], "score")

    # A lead the operator labels counts as theirs and leaves the list.
    label(session, apart[0], OTHER)
    after = spot_check(session, version=1, seed="1")

    assert apart[0].id not in {one.lead_id for one in after.disagreements}
