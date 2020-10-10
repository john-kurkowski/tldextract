'''tldextract integration tests.'''

import pytest

import tldextract


def test_bad_kwargs():
    with pytest.raises(ValueError):
        tldextract.TLDExtract(
            cache_dir=False, suffix_list_urls=False, fallback_to_snapshot=False
        )
