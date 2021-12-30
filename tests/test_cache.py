"""Test the caching functionality"""
import os.path
import sys
import types

import pytest
import tldextract.cache
from tldextract.cache import (DiskCache, get_cache_dir,
                              get_pkg_unique_identifier)


def test_disk_cache(tmpdir):
    cache = DiskCache(tmpdir)
    cache.set("testing", "foo", "bar")
    assert cache.get("testing", "foo") == "bar"

    cache.clear()

    with pytest.raises(KeyError):
        cache.get("testing", "foo")

    cache.set("testing", "foo", "baz")
    assert cache.get("testing", "foo") == "baz"


def test_get_pkg_unique_identifier(monkeypatch):
    monkeypatch.setattr(sys, "version_info", (3, 8, 1, "final", 0))
    monkeypatch.setattr(sys, "prefix", "/home/john/.pyenv/versions/myvirtualenv")

    mock_version_module = types.ModuleType("tldextract._version", "mocked module")
    mock_version_module.version = "1.2.3"
    monkeypatch.setitem(sys.modules, "tldextract._version", mock_version_module)

    assert (
        get_pkg_unique_identifier()
        == "3.8.1.final__myvirtualenv__f01a7b__tldextract-1.2.3"
    )


def test_get_cache_dir(monkeypatch):
    pkg_identifier = "3.8.1.final__myvirtualenv__f01a7b__tldextract-1.2.3"
    monkeypatch.setattr(
        tldextract.cache, "get_pkg_unique_identifier", lambda: pkg_identifier
    )

    # with no HOME set, fallback to attempting to use package directory itself
    monkeypatch.delenv("HOME", raising=False)
    monkeypatch.delenv("XDG_CACHE_HOME", raising=False)
    monkeypatch.delenv("TLDEXTRACT_CACHE", raising=False)
    assert get_cache_dir().endswith("tldextract/.suffix_cache/")

    # with home set, but not anything else specified, use XDG_CACHE_HOME default
    monkeypatch.setenv("HOME", "/home/john")
    monkeypatch.delenv("XDG_CACHE_HOME", raising=False)
    monkeypatch.delenv("TLDEXTRACT_CACHE", raising=False)
    assert get_cache_dir() == os.path.join(
        "/home/john", ".cache/python-tldextract", pkg_identifier
    )

    # if XDG_CACHE_HOME is set, use it
    monkeypatch.setenv("HOME", "/home/john")
    monkeypatch.setenv("XDG_CACHE_HOME", "/my/alt/cache")
    monkeypatch.delenv("TLDEXTRACT_CACHE", raising=False)

    assert get_cache_dir() == os.path.join(
        "/my/alt/cache/python-tldextract", pkg_identifier
    )

    # if TLDEXTRACT_CACHE is set, use it
    monkeypatch.setenv("HOME", "/home/john")
    monkeypatch.setenv("XDG_CACHE_HOME", "/my/alt/cache")
    monkeypatch.setenv("TLDEXTRACT_CACHE", "/alt-tld-cache")

    assert get_cache_dir() == "/alt-tld-cache"
