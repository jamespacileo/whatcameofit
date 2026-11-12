"""What a page says about itself, tested through `read_page`, and whether a registry record
agrees with what an article says of its trial, tested through `agreeing`. Both are pure.

Scenario names are from openspec live-lookup. Every page here is synthetic.
"""

from thenwhat.extract.page import read_page
from thenwhat.lookup.details import Details, agreeing

BODY = "Researchers gave EX-1 to 120 people born without some teeth. " * 12
PAGE = f"""<html><head>
<title>Antibody regrows teeth | The Example</title>
<meta property="og:title" content="Antibody regrows teeth in first human trial">
<meta name="description" content="A drug called EX-1 restored missing teeth, a study says.">
<meta property="article:published_time" content="2026-03-04T09:30:00Z">
<script type="application/ld+json">
{{"@context": "https://schema.org", "@graph": [
  {{"@type": "Organization", "name": "The Example"}},
  {{"@type": "NewsArticle", "headline": "Antibody regrows teeth", "datePublished": "2026-03-04",
    "articleBody": "{BODY.strip()}"}}]}}
</script>
<script>var tracking = "not for readers";</script>
</head><body>
<nav>Home News Sport</nav>
<p>Subscribe to read the full story.</p>
<p>The results were <a href="https://doi.org/10.1234/example.2026.0042">published</a> in a
journal and the study is <a href="https://clinicaltrials.gov/study/NCT01234567">registered</a>.
An <a href="https://pubmed.ncbi.nlm.nih.gov/31234567/">earlier report</a> covered mice.</p>
</body></html>"""


def test_a_page_names_its_headline_summary_and_date_in_its_tags():
    """Scenario: Page that describes itself in its tags"""
    page = read_page(PAGE)

    assert page.headline == "Antibody regrows teeth in first human trial"
    assert page.summary == "A drug called EX-1 restored missing teeth, a study says."
    assert page.published == "2026-03-04T09:30:00Z"


def test_a_page_without_tags_falls_back_to_its_title():
    page = read_page("<html><head><title>Teeth regrown</title></head><body><p>Hi</p></body></html>")

    assert (page.headline, page.summary, page.published, page.body) == (
        "Teeth regrown",
        None,
        None,
        None,
    )


def test_the_article_carried_as_structured_data_is_read_in_place_of_a_teaser():
    """Scenario: Page that carries the article as structured data"""
    page = read_page(PAGE)

    assert page.body == BODY.strip()
    text = page.as_text()
    assert text.startswith("Headline: Antibody regrows teeth in first human trial\n")
    assert "Published: 2026-03-04T09:30:00Z" in text
    assert "gave EX-1 to 120 people" in text
    assert "Subscribe to read" not in text and "tracking" not in text


def test_malformed_structured_data_leaves_the_visible_text():
    page = read_page(
        '<html><body><script type="application/ld+json">{not json</script>'
        "<p>EX-1 regrew teeth.</p></body></html>"
    )

    assert (page.body, page.as_text()) == (None, "EX-1 regrew teeth.")


def test_links_to_a_paper_and_to_the_registry_are_found():
    """Scenario: Page that links to the paper it reports"""
    page = read_page(PAGE)

    assert page.dois == ("10.1234/example.2026.0042",)
    assert page.pubmed_ids == ("31234567",)
    assert page.registry_numbers == ("NCT01234567",)


def test_a_publisher_address_that_holds_the_doi_is_read():
    links = [
        "https://www.nejm.org/doi/full/10.1056/NEJMoa2206038?query=featured",
        "https://www.nature.com/articles/s41591-023-02427-9",
        "https://www.thelancet.com/journals/lancet/article/PIIS0140-6736(23)01053-X/fulltext",
    ]
    page = read_page("".join(f'<a href="{link}">paper</a>' for link in links))

    assert page.dois == (
        "10.1056/nejmoa2206038",
        "10.1038/s41591-023-02427-9",
        "10.1016/s0140-6736(23)01053-x",
    )


def record(acronym=None, title="EX-1 in tooth agenesis", count=None, lead=None, others=()):
    return {
        "protocolSection": {
            "identificationModule": {
                "nctId": "NCT00000001",
                "briefTitle": title,
                "acronym": acronym,
            },
            "designModule": {"enrollmentInfo": {"count": count}},
            "sponsorCollaboratorsModule": {
                "leadSponsor": {"name": lead},
                "collaborators": [{"name": name} for name in others],
            },
        }
    }


def test_a_record_agrees_with_the_trial_name_by_acronym_or_title():
    """Scenario: Text that names the trial"""
    named = Details(trial_name="REGROW-2")

    assert agreeing(record(acronym="REGROW-2"), named) == ["trial_name"]
    assert agreeing(record(title="EX-1 in adults (REGROW-2)"), named) == ["trial_name"]
    assert agreeing(record(acronym="REGROW-21"), named) == []
    assert agreeing(record(acronym="REGROW-2"), Details()) == []


def test_a_record_agrees_with_a_number_of_participants_within_a_tenth():
    """Scenario: Text that gives the trial's size and who ran it"""
    assert agreeing(record(count=2539), Details(participants=2500)) == ["participants"]
    assert agreeing(record(count=751), Details(participants=2500)) == []
    assert agreeing(record(count=None), Details(participants=2500)) == []


def test_a_record_agrees_with_a_sponsor_named_in_other_words():
    wanted = Details(sponsor="Oxford University")

    assert agreeing(record(lead="University of Oxford"), wanted) == ["sponsor"]
    assert agreeing(record(lead="Example Pharma", others=["University of Oxford"]), wanted) == [
        "sponsor"
    ]
    assert agreeing(record(lead="Oxford Immunotec Ltd"), wanted) == []
    assert agreeing(record(lead="Eli Lilly and Company"), Details(sponsor="Eli Lilly")) == [
        "sponsor"
    ]
