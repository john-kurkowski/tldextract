"""tldextract unit tests with a custom suffix list."""

import os
import tempfile
from pathlib import Path

import pytest

import tldextract
from tldextract.tldextract import ExtractResult

FAKE_SUFFIX_LIST_URL = Path(
    os.path.dirname(os.path.abspath(__file__)),
    "fixtures",
    "fake_suffix_list_fixture.dat",
).as_uri()

EXTRA_SUFFIXES = ["foo1", "bar1", "baz1"]

extract_using_fake_suffix_list = tldextract.TLDExtract(
    cache_dir=tempfile.mkdtemp(), suffix_list_urls=[FAKE_SUFFIX_LIST_URL]
)
extract_using_fake_suffix_list_no_cache = tldextract.TLDExtract(
    cache_dir=None, suffix_list_urls=[FAKE_SUFFIX_LIST_URL]
)
extract_using_extra_suffixes = tldextract.TLDExtract(
    cache_dir=None,
    suffix_list_urls=[FAKE_SUFFIX_LIST_URL],
    extra_suffixes=EXTRA_SUFFIXES,
)


def test_private_extraction() -> None:
    """Test this library's uncached, offline, private domain extraction."""
    tld = tldextract.TLDExtract(cache_dir=tempfile.mkdtemp(), suffix_list_urls=[])

    assert tld("foo.blogspot.com") == ExtractResult(
        subdomain="foo",
        domain="blogspot",
        suffix="com",
        is_private=False,
        registry_suffix="com",
    )
    assert tld("foo.blogspot.com", include_psl_private_domains=True) == ExtractResult(
        subdomain="",
        domain="foo",
        suffix="blogspot.com",
        is_private=True,
        registry_suffix="com",
    )


def test_suffix_which_is_not_in_custom_list() -> None:
    """Test a custom suffix list without .com."""
    for fun in (
        extract_using_fake_suffix_list,
        extract_using_fake_suffix_list_no_cache,
    ):
        result = fun("www.google.com")
        assert result.suffix == ""


def test_custom_suffixes() -> None:
    """Test a custom suffix list with common, metasyntactic suffixes."""
    for fun in (
        extract_using_fake_suffix_list,
        extract_using_fake_suffix_list_no_cache,
    ):
        for custom_suffix in ("foo", "bar", "baz"):
            result = fun("www.foo.bar.baz.quux" + "." + custom_suffix)
            assert result.suffix == custom_suffix


def test_suffix_which_is_not_in_extra_list() -> None:
    """Test a custom suffix list and extra suffixes without .com."""
    result = extract_using_extra_suffixes("www.google.com")
    assert result.suffix == ""


def test_extra_suffixes() -> None:
    """Test extra suffixes."""
    for custom_suffix in EXTRA_SUFFIXES:
        netloc = "www.foo.bar.baz.quux" + "." + custom_suffix
        result = extract_using_extra_suffixes(netloc)
        assert result.suffix == custom_suffix


@pytest.mark.parametrize("include_private", [False, True])
@pytest.mark.parametrize(
    ("hostname", "private_components", "public_subdomain"),
    [
        ("region.example.com", ("", "region", "example.com"), "region"),
        (
            "tenant.region.example.com",
            ("tenant", "region", "example.com"),
            "tenant.region",
        ),
        (
            "tenant.service.region.example.com",
            ("", "tenant", "service.region.example.com"),
            "tenant.service.region",
        ),
    ],
)
def test_private_suffix_metadata_after_partial_match(
    tmp_path: Path,
    include_private: bool,
    hostname: str,
    private_components: tuple[str, str, str],
    public_subdomain: str,
) -> None:
    """A partial match of a longer rule preserves the matching suffix's metadata."""
    suffix_list = tmp_path / "suffixes.dat"
    suffix_list.write_text(
        "com\n// ===BEGIN PRIVATE DOMAINS===\nexample.com\nservice.region.example.com\n",
        encoding="utf-8",
    )
    extractor = tldextract.TLDExtract(
        cache_dir=None,
        suffix_list_urls=[suffix_list.as_uri()],
        fallback_to_snapshot=False,
        include_psl_private_domains=include_private,
    )
    subdomain, domain, suffix = (
        private_components if include_private else (public_subdomain, "example", "com")
    )
    result = extractor(hostname)
    assert result == ExtractResult(
        subdomain=subdomain,
        domain=domain,
        suffix=suffix,
        is_private=include_private,
        registry_suffix="com",
    )
    assert result.top_domain_under_registry_suffix == "example.com"
