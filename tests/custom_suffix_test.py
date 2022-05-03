"""tldextract unit tests with a custom suffix list."""

import os
import tempfile

import tldextract

FAKE_SUFFIX_LIST_URL = "file://" + os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "fixtures/fake_suffix_list_fixture.dat"
)
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


def test_private_extraction():
    tld = tldextract.TLDExtract(cache_dir=tempfile.mkdtemp(), suffix_list_urls=[])

    assert tld("foo.blogspot.com") == ("foo", "blogspot", "com")
    assert tld("foo.blogspot.com", include_psl_private_domains=True) == (
        "",
        "foo",
        "blogspot.com",
    )


def test_suffix_which_is_not_in_custom_list():
    for fun in (
        extract_using_fake_suffix_list,
        extract_using_fake_suffix_list_no_cache,
    ):
        result = fun("www.google.com")
        assert result.suffix == ""


def test_custom_suffixes():
    for fun in (
        extract_using_fake_suffix_list,
        extract_using_fake_suffix_list_no_cache,
    ):
        for custom_suffix in ("foo", "bar", "baz"):
            result = fun("www.foo.bar.baz.quux" + "." + custom_suffix)
            assert result.suffix == custom_suffix


def test_suffix_which_is_not_in_extra_list():
    result = extract_using_extra_suffixes("www.google.com")
    assert result.suffix == ""


def test_extra_suffixes():
    for custom_suffix in EXTRA_SUFFIXES:
        netloc = "www.foo.bar.baz.quux" + "." + custom_suffix
        result = extract_using_extra_suffixes(netloc)
        assert result.suffix == custom_suffix
