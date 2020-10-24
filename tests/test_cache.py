"""Test the caching functionality"""
import pytest
from tldextract.cache import DiskCache


def test_disk_cache(tmpdir):
    cache = DiskCache(tmpdir)
    cache.set("testing", "foo", "bar")
    assert cache.get("testing", "foo") == "bar"

    cache.clear()

    with pytest.raises(KeyError):
        cache.get("testing", "foo")

    cache.set("testing", "foo", "baz")
    assert cache.get("testing", "foo") == "baz"
