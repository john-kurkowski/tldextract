"""tldextract unit tests with a custom suffix list."""

import os
import tempfile
from pathlib import Path

import tldextract
from tldextract.suffix_list import PslMetadata, SuffixListInfo
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


def test_suffix_list_info_for_custom_file_without_official_metadata() -> None:
    """Report the effective custom file source without PSL header metadata."""
    assert extract_using_fake_suffix_list.suffix_list_info == SuffixListInfo(
        loaded_from=FAKE_SUFFIX_LIST_URL,
        psl_metadata=None,
    )


def test_suffix_list_info_ignores_extra_suffixes() -> None:
    """Report list metadata independently from extra suffix configuration."""
    assert extract_using_extra_suffixes.suffix_list_info == SuffixListInfo(
        loaded_from=FAKE_SUFFIX_LIST_URL,
        psl_metadata=None,
    )


def test_suffix_list_info_with_partial_official_metadata(tmp_path: Path) -> None:
    """Expose VERSION even when COMMIT is omitted."""
    suffix_list = tmp_path / "partial_metadata.dat"
    suffix_list.write_text("// VERSION: 2025-02-03_04-05-06_UTC\ncom\n")
    extract = tldextract.TLDExtract(
        cache_dir=None, suffix_list_urls=[suffix_list.as_uri()]
    )

    assert extract.suffix_list_info == SuffixListInfo(
        loaded_from=suffix_list.as_uri(),
        psl_metadata=PslMetadata(version="2025-02-03_04-05-06_UTC", commit=None),
    )


def test_suffix_list_info_without_version_has_no_psl_metadata(tmp_path: Path) -> None:
    """Ignore header-like metadata when VERSION is missing."""
    suffix_list = tmp_path / "commit_only.dat"
    suffix_list.write_text("// COMMIT: abc123\ncom\n")
    extract = tldextract.TLDExtract(
        cache_dir=None, suffix_list_urls=[suffix_list.as_uri()]
    )

    assert extract.suffix_list_info == SuffixListInfo(
        loaded_from=suffix_list.as_uri(),
        psl_metadata=None,
    )
