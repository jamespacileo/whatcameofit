"""What kind of outlet a domain is: general news, health or clinical trade press, or a
press release wire. A checked-in list, applied by rule; no model decides it. A domain
on no list is unknown. Behavior: openspec article-leads, "Outlet kind".

The split matters because the tracker is about what readers were told: a registry-first
backfill is only worth running if general news, not only the trade press, covered the
trials. Add a domain here when `thenwhat backfill leads` shows it among the unknown.
"""

from urllib.parse import urlsplit

from thenwhat.domain import OutletKind

GENERAL_NEWS = frozenset(
    [
        "abcnews.go.com",
        "aljazeera.com",
        "apnews.com",
        "bbc.co.uk",
        "bbc.com",
        "bloomberg.com",
        "cbc.ca",
        "cbsnews.com",
        "cnbc.com",
        "cnn.com",
        "dailymail.co.uk",
        "dailymail.com",
        "economist.com",
        "everydayhealth.com",
        "forbes.com",
        "foxnews.com",
        "ft.com",
        "healthday.com",
        "healthline.com",
        "independent.co.uk",
        "latimes.com",
        "livescience.com",
        "medicalnewstoday.com",
        "medicalxpress.com",
        "mirror.co.uk",
        "nbcnews.com",
        "newatlas.com",
        "news-medical.net",
        "newscientist.com",
        "newsweek.com",
        "npr.org",
        "nytimes.com",
        "reuters.com",
        "sciencealert.com",
        "sciencedaily.com",
        "scientificamerican.com",
        "scitechdaily.com",
        "sky.com",
        "statnews.com",
        "telegraph.co.uk",
        "theatlantic.com",
        "theconversation.com",
        "theguardian.com",
        "thetimes.co.uk",
        "time.com",
        "usatoday.com",
        "usnews.com",
        "washingtonpost.com",
        "webmd.com",
        "wired.com",
        "wsj.com",
        "yahoo.com",
    ]
)
TRADE_PRESS = frozenset(
    [
        "2minutemedicine.com",
        "ajmc.com",
        "ascopost.com",
        "biopharmadive.com",
        "biospace.com",
        "cancernetwork.com",
        "clinicaltrialsarena.com",
        "contemporarypediatrics.com",
        "drugtopics.com",
        "endpts.com",
        "fdanews.com",
        "fiercebiotech.com",
        "fiercepharma.com",
        "hcplive.com",
        "healio.com",
        "hmpgloballearningnetwork.com",
        "managedhealthcareexecutive.com",
        "mdedge.com",
        "medicaldialogues.in",
        "medpagetoday.com",
        "medscape.com",
        "mims.com",
        "onclive.com",
        "ophthalmologytimes.com",
        "pharmaceutical-technology.com",
        "pharmacytimes.com",
        "pharmatimes.com",
        "pharmexec.com",
        "targetedonc.com",
        "thepharmaletter.com",
    ]
)
PRESS_RELEASE = frozenset(
    [
        "accesswire.com",
        "businesswire.com",
        "einpresswire.com",
        "eurekalert.org",
        "globenewswire.com",
        "newswire.com",
        "prnewswire.com",
        "prweb.com",
    ]
)
# Patient-community news sites of one publisher share this ending, for example
# multiplesclerosisnewstoday.com. They report trials for patients of one condition.
TRADE_ENDINGS = ("newstoday.com",)


def outlet_of(url: str) -> str:
    """The outlet's domain as an address gives it, without "www."."""
    host = (urlsplit(url).hostname or "").lower()
    return host.removeprefix("www.")


def kind_of(domain: str) -> OutletKind:
    domain = domain.lower().removeprefix("www.")
    for listed, kind in (
        (PRESS_RELEASE, OutletKind.PRESS_RELEASE),
        (GENERAL_NEWS, OutletKind.GENERAL_NEWS),
        (TRADE_PRESS, OutletKind.TRADE_PRESS),
    ):
        if any(domain == entry or domain.endswith("." + entry) for entry in listed):
            return kind
    if domain.endswith(TRADE_ENDINGS):
        return OutletKind.TRADE_PRESS
    return OutletKind.UNKNOWN
