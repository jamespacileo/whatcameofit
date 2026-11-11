"""The test suite must not be able to reach the internet."""

import httpx
import pytest


def test_request_to_a_real_host_is_blocked():
    with pytest.raises(Exception) as raised:
        httpx.get("https://clinicaltrials.gov/api/v2/version", timeout=5)

    assert "Tests must replay fixtures" in str(raised.value)
