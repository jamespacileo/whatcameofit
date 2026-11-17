"""Why a link lead's read made no claim, as codes. Behavior: openspec lead-reading
(change one-work-runner), "Every lead's reason is a code".

Three classes (openspec work-ledger). Final: what the article is, or a page that is
gone. Put off: the site or the page reader cannot serve the page now, and the lead comes
back by itself. Needs a fix: a cause outside the article that can be put right, after
which the leads are made due with `thenwhat work requeue link_read --reason <code>`.

The words are the ones a lead's detail has always held, so a lead read before the codes
existed and one read after say the same thing.
"""

from thenwhat.work.outcome import Reason, ReasonClass

FINAL, LATER, NEEDS_FIX = ReasonClass.FINAL, ReasonClass.LATER, ReasonClass.NEEDS_FIX

# What a lead's detail says of a site's answer, whatever the answer means for the lead.
SITE_ANSWERED = "the page could not be retrieved (the site answered {status})"

# --- final: the lead is finished ------------------------------------------------------
ALREADY_TRACKED = Reason("already_tracked", FINAL, "its address is a claim's source article")
ENOUGH_ARTICLES = Reason("enough_articles", FINAL, "the claim it names has enough articles")
PAGE_GONE = Reason("page_gone", FINAL, SITE_ANSWERED)
NOT_ALLOWED = Reason("not_allowed", FINAL, "the page reader does not allow the address: {why}")
NOT_ONE_TREATMENT = Reason("not_one_treatment", FINAL, "not about one treatment for one condition")
BUSINESS_NEWS = Reason("business_news", FINAL, "business news about a treatment")
# Stays with the operator, who attaches or dismisses the article (openspec lead-reading).
IDENTITY_UNRESOLVED = Reason(
    "identity_unresolved", FINAL, "its names overlap a claim and the same claim was not established"
)

# --- put off: the lead comes back by itself -------------------------------------------
SITE_BUSY = Reason("site_busy", LATER, SITE_ANSWERED)
READER_NOT_NOW = Reason("reader_not_now", LATER, "the page reader could not get the page now")
OUTLET_HELD = Reason(
    "outlet_held", LATER, "not asked: the page reader says its outlet cannot be asked yet"
)
OUTLET_JUST_ASKED = Reason(
    "outlet_just_asked", LATER, "not asked: its outlet was asked a moment ago"
)

# --- needs a fix: waits to be made due ------------------------------------------------
SITE_REFUSED = Reason("site_refused", NEEDS_FIX, SITE_ANSWERED)
OUTLET_REFUSES = Reason(
    "outlet_refuses",
    NEEDS_FIX,
    "not asked: its outlet answered 401 to the page reader for {pages} pages and served none",
)
NO_DATE = Reason("no_date", NEEDS_FIX, "the page gives no publication date")
NO_HEADLINE = Reason("no_headline", NEEDS_FIX, "the page gives no headline")
THIN_PAGE = Reason("thin_page", NEEDS_FIX, "too little article text")
NO_OUTLET_NAME = Reason("no_outlet_name", NEEDS_FIX, "its outlet has no display name")
NEEDS_VERTICAL = Reason("needs_vertical", NEEDS_FIX, "no vertical was likely enough")

REASONS = (
    ALREADY_TRACKED,
    ENOUGH_ARTICLES,
    PAGE_GONE,
    NOT_ALLOWED,
    NOT_ONE_TREATMENT,
    BUSINESS_NEWS,
    IDENTITY_UNRESOLVED,
    SITE_BUSY,
    READER_NOT_NOW,
    OUTLET_HELD,
    OUTLET_JUST_ASKED,
    SITE_REFUSED,
    OUTLET_REFUSES,
    NO_DATE,
    NO_HEADLINE,
    THIN_PAGE,
    NO_OUTLET_NAME,
    NEEDS_VERTICAL,
)

# A page that is gone, or was never there.
GONE = frozenset({404, 410})
# A site that refuses whoever asks: for the reader to be let in, not for time to pass.
REFUSED = frozenset({400, 401, 402, 403, 405, 406, 407, 451})


def reason_for_status(status: int) -> Reason:
    """What a site's answer other than 200 means for the lead. Gone is final and a
    refusal needs a fix. Anything else is put off: busy (202), throttling (408, 425,
    429), failing (500 and up), and any answer whose meaning is not known, which is not
    recorded as final because it cannot be told from one that passes."""
    if status in GONE:
        return PAGE_GONE
    if status in REFUSED:
        return SITE_REFUSED
    return SITE_BUSY
