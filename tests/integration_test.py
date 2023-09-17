"""tldextract integration tests."""

import pytest

import tldextract


def test_bad_kwargs_no_way_to_fetch() -> None:
    """Test an impossible combination of kwargs that disable all ways to fetch data."""
    with pytest.raises(ValueError, match="disable all ways"):
        tldextract.TLDExtract(
            cache_dir=None, suffix_list_urls=(), fallback_to_snapshot=False
        )
