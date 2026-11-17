"""Give every link lead read before reasons were codes the code its stored words stand for.

Revision ID: 0037
Revises: 0036

Data only. A lead's ledger entry for the read gains the reason's code and the values it
carries, worked out from the lead's stored outcome and detail. Two kinds of lead change
how they stand (openspec lead-reading, change one-work-runner):

- A lead whose site was busy, throttling or failing (202, 408, 425, 429, 500 and up, and
  any answer whose meaning is not known) is put off, due from now, and is no longer said
  to be unreadable.
- A lead refused for a cause that can be put right (the site refused the reader, no
  date, no headline, too little text, no outlet name, no likely vertical) needs a fix,
  and is read again when `thenwhat work requeue link_read --reason <code>` makes it due.

Every other lead keeps its outcome and gains its code. The migration fails, changing
nothing, if a lead's entry is left without a code: none is given a catch-all.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0037"
down_revision: str | None = "0036"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

READ = "e.record_kind = 'link_lead' AND e.step = 'link_read' AND e.outcome = 'nothing_found'"
SITE = r"^the page could not be retrieved \(the site answered (\d+)\)$"
OUTLET_REFUSES = r"^not asked: its outlet answered 401 to the page reader for (\d+) pages"
NOT_ALLOWED = "the page reader does not allow the address: "
GONE = "(404, 410)"
REFUSED = "(400, 401, 402, 403, 405, 406, 407, 451)"
OUTLET = "jsonb_build_object('outlet', l.outlet)"

# The reason a detail's exact words stand for, each needing a fix.
BY_WORDS = (
    ("no_date", "the page gives no publication date"),
    ("no_headline", "the page gives no headline"),
    ("thin_page", "too little article text"),
    ("no_outlet_name", "its outlet has no display name"),
)
# The reason a read outcome stands for, and whether its lead is finished or needs a fix.
BY_OUTCOME = (
    ("enough_articles", "enough_articles", "nothing_found"),
    ("not_one_treatment", "not_one_treatment", "nothing_found"),
    ("business_news", "business_news", "nothing_found"),
    ("identity_unresolved", "identity_unresolved", "nothing_found"),
    ("needs_vertical", "needs_vertical", "needs_fix"),
)


def _status() -> str:
    return f"(substring(l.read_detail from '{SITE}'))::int"


def upgrade() -> None:
    # Audit could attach an unresolved lead after its unsuccessful read was recorded.
    # Its successful attachment takes precedence over the earlier ledger outcome.
    op.execute(
        f"""
        UPDATE work_entry e SET outcome = 'done', stale = false
        FROM link_lead l
        WHERE l.id = e.record_id AND {READ} AND l.read_outcome = 'added_to_claim'
        """
    )
    # A site's answer: gone is final, a refusal needs a fix, anything else is put off.
    op.execute(
        f"""
        UPDATE work_entry e SET
            reason = CASE WHEN {_status()} IN {GONE} THEN 'page_gone'
                          WHEN {_status()} IN {REFUSED} THEN 'site_refused'
                          ELSE 'site_busy' END,
            reason_values = {OUTLET} || jsonb_build_object('status', {_status()}),
            outcome = CASE WHEN {_status()} IN {GONE} THEN 'nothing_found'
                           WHEN {_status()} IN {REFUSED} THEN 'needs_fix'
                           ELSE 'later' END,
            attempts = CASE WHEN {_status()} IN {GONE} THEN e.attempts ELSE 0 END,
            not_before = CASE WHEN {_status()} IN {GONE} OR {_status()} IN {REFUSED}
                              THEN NULL ELSE now() END,
            first_put_off_at = CASE WHEN {_status()} IN {GONE} OR {_status()} IN {REFUSED}
                                    THEN NULL ELSE now() END
        FROM link_lead l
        WHERE l.id = e.record_id AND {READ} AND l.read_detail ~ '{SITE}'
        """
    )
    # A lead that is put off is not said to be unreadable: it has not been read yet.
    op.execute(
        """
        UPDATE link_lead l SET read_outcome = NULL, read_detail = NULL
        FROM work_entry e
        WHERE e.record_id = l.id AND e.record_kind = 'link_lead' AND e.step = 'link_read'
          AND e.outcome = 'later' AND e.reason = 'site_busy'
        """
    )
    op.execute(
        f"""
        UPDATE work_entry e SET reason = 'outlet_refuses', outcome = 'needs_fix', attempts = 0,
            reason_values = {OUTLET} || jsonb_build_object(
                'pages', (substring(l.read_detail from '{OUTLET_REFUSES}'))::int)
        FROM link_lead l
        WHERE l.id = e.record_id AND {READ} AND l.read_detail ~ '{OUTLET_REFUSES}'
        """
    )
    op.execute(
        f"""
        UPDATE work_entry e SET reason = 'not_allowed',
            reason_values = {OUTLET} || jsonb_build_object(
                'why', substr(l.read_detail, {len(NOT_ALLOWED) + 1}))
        FROM link_lead l
        WHERE l.id = e.record_id AND {READ} AND e.reason IS NULL
          AND starts_with(l.read_detail, '{NOT_ALLOWED}')
        """
    )
    for code, words in BY_WORDS:
        op.execute(
            f"""
            UPDATE work_entry e SET reason = '{code}', outcome = 'needs_fix', attempts = 0,
                reason_values = {OUTLET}
            FROM link_lead l
            WHERE l.id = e.record_id AND {READ} AND e.reason IS NULL
              AND l.read_outcome = 'cannot_be_read' AND l.read_detail = '{words}'
            """
        )
    for read_outcome, code, outcome in BY_OUTCOME:
        op.execute(
            f"""
            UPDATE work_entry e SET reason = '{code}', outcome = '{outcome}',
                attempts = CASE WHEN '{outcome}' = 'needs_fix' THEN 0 ELSE e.attempts END,
                reason_values = {OUTLET}
            FROM link_lead l
            WHERE l.id = e.record_id AND {READ} AND e.reason IS NULL
              AND l.read_outcome = '{read_outcome}'
            """
        )
    # A lead whose address had become a claim's source article when its turn came.
    op.execute(
        f"""
        UPDATE work_entry e SET reason = 'already_tracked'
        FROM link_lead l
        WHERE l.id = e.record_id AND {READ} AND e.reason IS NULL
          AND l.read_outcome IS NULL AND l.screen_outcome = 'already_tracked'
        """
    )
    # The news search found no story for a trial, and the paper search no paper.
    for step, code in (("news_search", "no_stories"), ("pubmed_papers", "no_papers")):
        op.execute(
            f"""
            UPDATE work_entry SET reason = '{code}'
            WHERE step = '{step}' AND outcome = 'nothing_found' AND reason IS NULL
            """
        )
    left = (
        op.get_bind()
        .exec_driver_sql(
            """
        SELECT coalesce(l.read_outcome, 'no outcome') || ': ' || coalesce(l.read_detail, ''),
               count(*)
        FROM work_entry e JOIN link_lead l ON l.id = e.record_id
        WHERE e.record_kind = 'link_lead' AND e.step = 'link_read'
          AND e.outcome = 'nothing_found' AND e.reason IS NULL
        GROUP BY 1 ORDER BY 2 DESC LIMIT 20
        """
        )
        .all()
    )
    if left:
        listed = "; ".join(f"{count} x {words!r}" for words, count in left)
        raise RuntimeError(
            "Some link leads' reads have no reason code for what they hold, so nothing was "
            f"changed: {listed}. Add each to this migration's mapping."
        )


def downgrade() -> None:
    # A lead that was put off for a site's answer is said to be unreadable again, in the
    # words it had.
    op.execute(
        """
        UPDATE link_lead l SET read_outcome = 'cannot_be_read',
            read_detail = 'the page could not be retrieved (the site answered '
                          || (e.reason_values->>'status') || ')'
        FROM work_entry e
        WHERE e.record_id = l.id AND e.record_kind = 'link_lead' AND e.step = 'link_read'
          AND e.outcome = 'later' AND e.reason = 'site_busy' AND l.read_outcome IS NULL
        """
    )
    op.execute(
        """
        UPDATE work_entry SET outcome = 'nothing_found', attempts = greatest(attempts, 1),
            not_before = NULL, first_put_off_at = NULL
        WHERE record_kind = 'link_lead' AND step = 'link_read'
          AND ((outcome = 'later' AND reason = 'site_busy') OR outcome = 'needs_fix')
        """
    )
    op.execute(
        """
        UPDATE work_entry SET reason = NULL, reason_values = NULL
        WHERE step IN ('link_read', 'news_search', 'pubmed_papers')
          AND outcome = 'nothing_found'
        """
    )
