"""What kind of outlet a domain is: general news, health or clinical trade press, or a
press release wire. A checked-in list, applied by rule; no model decides it. A domain
on no list is unknown. Behavior: openspec article-leads, "Outlet kind".

The split matters because the tracker is about what readers were told: a registry-first
backfill is only worth running if general news, not only the trade press, covered the
trials. Add a domain here when `thenwhat backfill leads` shows it among the unknown.
"""

from urllib.parse import urlsplit

from thenwhat.domain import OutletKind

# Raised whenever a domain is added to or taken off a list, so a backfill run records
# which lists it applied (openspec backfill-run-files).
OUTLET_LIST_VERSION = 1

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
        "cidrap.umn.edu",
        "cnbc.com",
        "cnn.com",
        "ctvnews.ca",
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
        "manilatimes.net",
        "medicalnewstoday.com",
        "medicalxpress.com",
        "mirror.co.uk",
        "nautil.us",
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
        # Added 2026-11-16, on the operator's decision of that day, from the unlisted domains
        # that shared links most often named a health word in their titles.
        "abc.net.au",
        "arstechnica.com",
        "axios.com",
        "businessinsider.com",
        "english.elpais.com",
        "gizmodo.com",
        "neurosciencenews.com",
        "newyorker.com",
        "nypost.com",
        "phys.org",
        "politico.com",
        "propublica.org",
        "qz.com",
        "scmp.com",
        "techcrunch.com",
        "technologyreview.com",
        "thehill.com",
        "theregister.com",
        "theverge.com",
        "vice.com",
        "vox.com",
    ]
)
TRADE_PRESS = frozenset(
    [
        "2minutemedicine.com",
        "ajmc.com",
        "ascopost.com",
        "biocentury.com",
        "biopharmadive.com",
        "biospace.com",
        "cancernetwork.com",
        "citeline.com",
        "clinicaltrialsarena.com",
        "contemporaryobgyn.net",
        "contemporarypediatrics.com",
        "dermatologytimes.com",
        "drugstorenews.com",
        "drugtopics.com",
        "empr.com",
        "endpts.com",
        "fdanews.com",
        "fiercebiotech.com",
        "fiercepharma.com",
        "genengnews.com",
        "hcplive.com",
        "healio.com",
        "hepmag.com",
        "hmpgloballearningnetwork.com",
        "managedhealthcareexecutive.com",
        "mdedge.com",
        "medicaldialogues.in",
        "medpagetoday.com",
        "medscape.com",
        "mims.com",
        "neurologyadvisor.com",
        "neurologylive.com",
        "onclive.com",
        "oncologypipeline.com",
        "ophthalmologytimes.com",
        "outsourcing-pharma.com",
        "pharmaceutical-business-review.com",
        "pharmaceutical-technology.com",
        "pharmacytimes.com",
        "pharmaintelligence.informa.com",
        "pharmatimes.com",
        "pharmexec.com",
        "practicaldermatology.com",
        "practicalneurology.com",
        "reachmd.com",
        "targetedonc.com",
        "thepharmaletter.com",
        "urologytimes.com",
        "urotoday.com",
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
        "prnewswire.co.uk",
        "prnewswire.com",
        "prweb.com",
        # Institutions' own news pages, added 2026-11-16 on the same decision.
        "directorsblog.nih.gov",
        "news.mit.edu",
    ]
)
# The name each listed outlet goes by, as a source article shows it: the name the
# outlet uses for itself, in the form entered articles already carry ("ScienceDaily",
# "The Guardian"). An article read from a link lead takes its outlet's name from here,
# and a lead whose outlet has no name here is not read (openspec lead-reading). Every
# domain listed above has a name; a test fails when one is added without.
OUTLET_NAMES: dict[str, str] = {
    # General news.
    "abcnews.go.com": "ABC News",
    "aljazeera.com": "Al Jazeera",
    "apnews.com": "Associated Press",
    "bbc.co.uk": "BBC News",
    "bbc.com": "BBC News",
    "bloomberg.com": "Bloomberg",
    "cbc.ca": "CBC News",
    "cbsnews.com": "CBS News",
    "cidrap.umn.edu": "CIDRAP",
    "cnbc.com": "CNBC",
    "cnn.com": "CNN",
    "ctvnews.ca": "CTV News",
    "dailymail.co.uk": "Daily Mail",
    "dailymail.com": "Daily Mail",
    "economist.com": "The Economist",
    "everydayhealth.com": "Everyday Health",
    "forbes.com": "Forbes",
    "foxnews.com": "Fox News",
    "ft.com": "Financial Times",
    "healthday.com": "HealthDay",
    "healthline.com": "Healthline",
    "independent.co.uk": "The Independent",
    "latimes.com": "Los Angeles Times",
    "livescience.com": "Live Science",
    "manilatimes.net": "The Manila Times",
    "medicalnewstoday.com": "Medical News Today",
    "medicalxpress.com": "Medical Xpress",
    "mirror.co.uk": "The Mirror",
    "nautil.us": "Nautilus",
    "nbcnews.com": "NBC News",
    "newatlas.com": "New Atlas",
    "news-medical.net": "News-Medical",
    "newscientist.com": "New Scientist",
    "newsweek.com": "Newsweek",
    "npr.org": "NPR",
    "nytimes.com": "The New York Times",
    "reuters.com": "Reuters",
    "sciencealert.com": "ScienceAlert",
    "sciencedaily.com": "ScienceDaily",
    "scientificamerican.com": "Scientific American",
    "scitechdaily.com": "SciTechDaily",
    "sky.com": "Sky News",
    "statnews.com": "STAT",
    "telegraph.co.uk": "The Telegraph",
    "theatlantic.com": "The Atlantic",
    "theconversation.com": "The Conversation",
    "theguardian.com": "The Guardian",
    "thetimes.co.uk": "The Times",
    "time.com": "Time",
    "usatoday.com": "USA Today",
    "usnews.com": "U.S. News & World Report",
    "washingtonpost.com": "The Washington Post",
    "webmd.com": "WebMD",
    "wired.com": "Wired",
    "wsj.com": "The Wall Street Journal",
    "yahoo.com": "Yahoo News",
    # Health and clinical trade press.
    "2minutemedicine.com": "2 Minute Medicine",
    "ajmc.com": "AJMC",
    "ascopost.com": "The ASCO Post",
    "biocentury.com": "BioCentury",
    "biopharmadive.com": "BioPharma Dive",
    "biospace.com": "BioSpace",
    "cancernetwork.com": "CancerNetwork",
    "citeline.com": "Citeline",
    "clinicaltrialsarena.com": "Clinical Trials Arena",
    "contemporaryobgyn.net": "Contemporary OB/GYN",
    "contemporarypediatrics.com": "Contemporary Pediatrics",
    "dermatologytimes.com": "Dermatology Times",
    "drugstorenews.com": "Drug Store News",
    "drugtopics.com": "Drug Topics",
    "empr.com": "MPR",
    "endpts.com": "Endpoints News",
    "fdanews.com": "FDAnews",
    "fiercebiotech.com": "Fierce Biotech",
    "fiercepharma.com": "Fierce Pharma",
    "genengnews.com": "Genetic Engineering & Biotechnology News",
    "hcplive.com": "HCPLive",
    "healio.com": "Healio",
    "hepmag.com": "Hep",
    "hmpgloballearningnetwork.com": "HMP Global Learning Network",
    "managedhealthcareexecutive.com": "Managed Healthcare Executive",
    "mdedge.com": "MDedge",
    "medicaldialogues.in": "Medical Dialogues",
    "medpagetoday.com": "MedPage Today",
    "medscape.com": "Medscape",
    "mims.com": "MIMS",
    "neurologyadvisor.com": "Neurology Advisor",
    "neurologylive.com": "NeurologyLive",
    "onclive.com": "OncLive",
    "oncologypipeline.com": "Oncology Pipeline",
    "ophthalmologytimes.com": "Ophthalmology Times",
    "outsourcing-pharma.com": "Outsourcing-Pharma",
    "pharmaceutical-business-review.com": "Pharmaceutical Business Review",
    "pharmaceutical-technology.com": "Pharmaceutical Technology",
    "pharmacytimes.com": "Pharmacy Times",
    "pharmaintelligence.informa.com": "Pharma Intelligence",
    "pharmatimes.com": "PharmaTimes",
    "pharmexec.com": "Pharmaceutical Executive",
    "practicaldermatology.com": "Practical Dermatology",
    "practicalneurology.com": "Practical Neurology",
    "reachmd.com": "ReachMD",
    "targetedonc.com": "Targeted Oncology",
    "thepharmaletter.com": "The Pharma Letter",
    "urologytimes.com": "Urology Times",
    "urotoday.com": "UroToday",
    # Press release wires.
    "accesswire.com": "Accesswire",
    "businesswire.com": "Business Wire",
    "einpresswire.com": "EIN Presswire",
    "eurekalert.org": "EurekAlert",
    "globenewswire.com": "GlobeNewswire",
    "newswire.com": "Newswire",
    "prnewswire.co.uk": "PR Newswire",
    "prnewswire.com": "PR Newswire",
    "prweb.com": "PRWeb",
    # Added 2026-11-16.
    "abc.net.au": "ABC News (Australia)",
    "arstechnica.com": "Ars Technica",
    "axios.com": "Axios",
    "businessinsider.com": "Business Insider",
    "directorsblog.nih.gov": "NIH Director's Blog",
    "english.elpais.com": "El País",
    "gizmodo.com": "Gizmodo",
    "neurosciencenews.com": "Neuroscience News",
    "news.mit.edu": "MIT News",
    "newyorker.com": "The New Yorker",
    "nypost.com": "New York Post",
    "phys.org": "Phys.org",
    "politico.com": "Politico",
    "propublica.org": "ProPublica",
    "qz.com": "Quartz",
    "scmp.com": "South China Morning Post",
    "techcrunch.com": "TechCrunch",
    "technologyreview.com": "MIT Technology Review",
    "thehill.com": "The Hill",
    "theregister.com": "The Register",
    "theverge.com": "The Verge",
    "vice.com": "Vice",
    "vox.com": "Vox",
}

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


def name_of(domain: str) -> str | None:
    """The display name of the listed outlet a domain belongs to, or None when the
    outlet has no name: a domain on no list, or one listed only by its ending. No name
    is made up from a domain."""
    domain = domain.lower().removeprefix("www.")
    for listed, name in OUTLET_NAMES.items():
        if domain == listed or domain.endswith("." + listed):
            return name
    return None
