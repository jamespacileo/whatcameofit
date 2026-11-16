"""The form in which two article addresses are compared: one link lead per key.
Behavior: openspec link-leads, "Addresses are compared as the site compares them".

This is the site's `site/src/lib/article-key.mjs` in Python. The two are tested on one
cases file (`site/tests/fixtures/article-key-cases.json`), so a change to either that
makes them disagree fails a test. Change both together.
"""

import re
from urllib.parse import parse_qsl, quote, urlsplit, urlunsplit

# Which form of the key this is. Raise it with every change that gives a stored address
# another key: link leads record the form they were keyed under, and loading is refused
# until `thenwhat backfill rekey-links` has brought the stored leads up to date.
# 2: more tracking parameters, outlets' own parameters, editions and renamed hosts,
#    doubled slashes and the letter case of escapes (after the run of 2026-11-16).
KEY_VERSION = 2

# Parameters that describe how a reader arrived, not which article this is.
TRACKING = re.compile(
    r"^(utm_.+|fbclid|gclid|dclid|msclkid|mc_cid|mc_eid|igshid|ref|ref_src|ref_url|referrer"
    r"|cmpid|cmp|ocid|smid|smtyp|ito|share|share_.+|at_.+|ns_.+|amp|amp_.+|outputtype|usqp"
    r"|mibextid|xtor|guccounter|guce_.+|soc_src|soc_trk|tsrc|ncid|sr_share|taid"
    r"|unlocked_article_code|emc|partner|rss"
    # Added after the run of 2026-11-16, each seen separating two leads for one article.
    r"|_r|pgtype|wt\..+|contentcollection|contentplacement|clicksource|rref|mbid|fsrc"
    r"|nlid|hpid|hpw|em_pos|nl_art|mtrref|smprod|gwh|gwt|mabreward|__twitter_impression"
    r"|postshare|trk|trk_.+|__source|srnd|intcid|icid|ribbon-ad-idx|moduledetail|eventname"
    r"|_ga|_gl|mkt_tok|yclid|twclid|gbraid|wbraid|_hsenc|_hsmi|hsctatracking|sref"
    r"|leadsource|s_cid|spm|wpisrc|wpmm|wprss|wpmk|referringsource|accesstoken|reflink"
    r"|cndid|spjobid|spmailingid|spreportid|spuserid|google_editors_picks|lipi|hootpostid"
    r"|sharetoken|emailtoken|cx_.+)$",
    re.IGNORECASE,
)
# Parameters that say how a reader arrived, or which page of one article is shown, on one
# outlet only. Elsewhere a parameter of the same name may name the article.
OUTLET_TRACKING = {
    "nytimes.com": re.compile(
        r"^(action|module|region|version|hp|referer|nl|te|src|pagewanted)$", re.IGNORECASE
    ),
    "wsj.com": re.compile(r"^mod$", re.IGNORECASE),
    "theatlantic.com": re.compile(r"^single_page$", re.IGNORECASE),
    "newyorker.com": re.compile(r"^currentpage$", re.IGNORECASE),
    "washingtonpost.com": re.compile(r"^(tid|noredirect)$", re.IGNORECASE),
    "economist.com": re.compile(r"^(frsc|cid1)$", re.IGNORECASE),
    "statnews.com": re.compile(r"^mod$", re.IGNORECASE),
}
# A parameter copied out of a page's source keeps the "amp;" of its "&amp;".
ESCAPED_AMPERSAND = re.compile(r"^(amp;)+", re.IGNORECASE)
# Leading host labels that serve the same article as the bare host.
SAME_SITE_LABELS = re.compile(r"^(www|m|mobile|amp|edition)\.")
# Hosts that serve one site under two names: an edition, a mobile or text form, a
# renamed site. Each was seen serving one article at one path under both names.
HOST_ALIASES = {
    "bbc.co.uk": "bbc.com",
    "us.cnn.com": "cnn.com",
    "lite.cnn.com": "cnn.com",
    "www-m.cnn.com": "cnn.com",
    "edition-m.cnn.com": "cnn.com",
    "uk.businessinsider.com": "businessinsider.com",
    "nordic.businessinsider.com": "businessinsider.com",
    "beta.washingtonpost.com": "washingtonpost.com",
    "beta.techcrunch.com": "techcrunch.com",
    "social.techcrunch.com": "techcrunch.com",
    "eu.usatoday.com": "usatoday.com",
    "text.npr.org": "npr.org",
    "motherboard.vice.com": "vice.com",
    "tonic.vice.com": "vice.com",
    "europe.newsweek.com": "newsweek.com",
    "institutions.newscientist.com": "newscientist.com",
    "beta.scmp.com": "scmp.com",
    "beta.latimes.com": "latimes.com",
    "next.ft.com": "ft.com",
    "prime.nautil.us": "nautil.us",
    "x.com": "twitter.com",
    "old.reddit.com": "reddit.com",
    "new.reddit.com": "reddit.com",
    "np.reddit.com": "reddit.com",
}
ESCAPE = re.compile(r"%[0-9a-fA-F]{2}")

YOUTUBE_HOSTS = ("youtube.com", "www.youtube.com", "m.youtube.com")
VIDEO_ID = re.compile(r"^[\w-]{11}$", re.ASCII)
VIDEO_PATH = re.compile(r"^/(?:shorts|live|embed)/([\w-]{11})/?$", re.ASCII)
SHORT_VIDEO_PATH = re.compile(r"^/([\w-]{11})/?$", re.ASCII)
# What JavaScript's encodeURIComponent leaves as it is, beyond letters and digits.
UNRESERVED = "-_.!~*'()"
# What a browser leaves as it is in a path.
PATH_SAFE = "/%:@!$&'()*+,;=-._~"


def _youtube_key(parts, query: list[tuple[str, str]]) -> str | None:
    """One YouTube video, whatever form its address takes."""
    if parts.username or parts.password or parts.port:
        return None
    host = (parts.hostname or "").lower()
    path = parts.path or "/"
    video = None
    if host == "youtu.be":
        found = SHORT_VIDEO_PATH.match(path)
        video = found.group(1) if found else None
    elif host in YOUTUBE_HOSTS:
        given = [value for name, value in query if name == "v"]
        if path == "/watch" and len(given) == 1:
            video = given[0]
        else:
            found = VIDEO_PATH.match(path)
            video = found.group(1) if found else None
    if not video or not VIDEO_ID.match(video):
        return None
    # An id in the path and another in the query are ambiguous, even on a known host.
    if path != "/watch" and any(name == "v" for name, _ in query):
        return None
    return f"youtube.com/watch?v={video}"


def _order(name: str) -> tuple[str, str]:
    """Parameter names in the order the site sorts them: without regard to letter case,
    lower case first where two names differ only in case."""
    return (name.casefold(), name.swapcase())


def _says_how_a_reader_arrived(name: str, host: str) -> bool:
    outlet = OUTLET_TRACKING.get(host)
    return bool(TRACKING.match(name) or (outlet and outlet.match(name)))


def article_key(address: str) -> str | None:
    """The host and path of an address in comparison form, or None when the address is
    not an http or https page."""
    try:
        parts = urlsplit(address.strip())
        host = (parts.hostname or "").lower()
        _ = parts.port  # raises for a port that is not a number
    except ValueError:
        return None
    if parts.scheme.lower() not in ("http", "https") or not host:
        return None
    query = parse_qsl(parts.query, keep_blank_values=True)

    video = _youtube_key(parts, query)
    if video:
        return video

    host = host.strip(".")
    while SAME_SITE_LABELS.match(host):
        host = SAME_SITE_LABELS.sub("", host, count=1)
    host = HOST_ALIASES.get(host, host)
    if not host:
        return None

    path = quote(parts.path, safe=PATH_SAFE)
    # An escape is the same character in either letter case, and a doubled slash the
    # same place as a single one.
    path = ESCAPE.sub(lambda escape: escape.group().upper(), path)
    path = re.sub(r"/{2,}", "/", path)
    path = re.sub(r"/+$", "", path)
    path = re.sub(r"/index\.html?$", "", path, flags=re.IGNORECASE)
    path = re.sub(r"(/amp|\.amp)$", "", path, flags=re.IGNORECASE)
    path = re.sub(r"^/amp(?=/)", "", path, flags=re.IGNORECASE)
    # CNN's AMP host repeats the site name as the first part of the path.
    if host == "cnn.com":
        path = re.sub(r"^/cnn(?=/)", "", path)
    # A Daily Mail article is its number; the words after it vary and are often cut short.
    if host == "dailymail.co.uk":
        mail = re.search(r"/article-(\d+)(/|$)", path)
        if mail:
            path = f"/article-{mail.group(1)}"

    kept = sorted(
        (
            (name, value)
            for name, value in ((ESCAPED_AMPERSAND.sub("", name), value) for name, value in query)
            if not _says_how_a_reader_arrived(name, host)
        ),
        key=lambda pair: _order(pair[0]),
    )
    rest = "&".join(
        f"{quote(name, safe=UNRESERVED)}={quote(value, safe=UNRESERVED)}" for name, value in kept
    )
    return host + path + (f"?{rest}" if rest else "")


def without_tracking(address: str) -> str:
    """An address as it is published with a source article: the address as shared, less
    its fragment and the parameters that say how a reader arrived. Those parameters can
    name the platform a link was shared on, which the export must not say."""
    parts = urlsplit(address.strip())
    kept = [
        (name, value)
        for name, value in parse_qsl(parts.query, keep_blank_values=True)
        if not TRACKING.match(name)
    ]
    query = "&".join(
        f"{quote(name, safe=UNRESERVED)}={quote(value, safe=UNRESERVED)}" for name, value in kept
    )
    return urlunsplit((parts.scheme, parts.netloc, parts.path, query, ""))
