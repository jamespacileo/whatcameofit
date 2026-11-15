"""The pipeline's address key, on the cases the site's own comparison is tested on
(site/tests/article-key-cases.test.mjs). Scenario names are from openspec link-leads."""

import json
from pathlib import Path

import pytest

from thenwhat.backfill.address import article_key

CASES = json.loads(
    (
        Path(__file__).resolve().parents[2]
        / "site"
        / "tests"
        / "fixtures"
        / "article-key-cases.json"
    ).read_text()
)
SAME = [(group["key"], address) for group in CASES["same"] for address in group["addresses"]]


@pytest.mark.parametrize(("key", "address"), SAME)
def test_every_shared_form_of_one_article_gives_its_key(key: str, address: str):
    """Scenario: A tracking parameter"""
    assert article_key(address) == key


@pytest.mark.parametrize("address", CASES["none"])
def test_an_address_that_is_not_a_web_page_has_no_key(address: str):
    """Scenario: An address that cannot be an article"""
    assert article_key(address) is None


def test_an_address_with_no_host_or_a_bad_port_has_no_key():
    assert article_key("https:///news/story") is None
    assert article_key("https://example.org:port/news") is None
