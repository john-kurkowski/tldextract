"""Main tldextract unit tests."""

from __future__ import annotations

import logging
import os
import tempfile
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest
import pytest_mock
import responses

import tldextract
import tldextract.suffix_list
from tldextract.cache import DiskCache
from tldextract.remote import inet_pton, lenient_netloc, looks_like_ip
from tldextract.suffix_list import SuffixListNotFound
from tldextract.tldextract import ExtractResult

extract = tldextract.TLDExtract(cache_dir=tempfile.mkdtemp())
extract_no_cache = tldextract.TLDExtract(cache_dir=None)
extract_using_real_local_suffix_list = tldextract.TLDExtract(
    cache_dir=tempfile.mkdtemp()
)
extract_using_real_local_suffix_list_no_cache = tldextract.TLDExtract(cache_dir=None)
extract_using_fallback_to_snapshot_no_cache = tldextract.TLDExtract(
    cache_dir=None, suffix_list_urls=()
)


def assert_extract(
    url: str,
    expected_domain_data: tuple[str, str, str, str],
    expected_ip_data: str = "",
    expected_ipv6_data: str = "",
    funs: Sequence[tldextract.TLDExtract] = (
        extract,
        extract_no_cache,
        extract_using_real_local_suffix_list,
        extract_using_real_local_suffix_list_no_cache,
        extract_using_fallback_to_snapshot_no_cache,
    ),
) -> None:
    """Test helper to compare all expected and actual attributes of an extraction.

    Runs the same comparison across several permutations of tldextract instance
    configurations.
    """
    (
        expected_fqdn,
        expected_subdomain,
        expected_domain,
        expected_tld,
    ) = expected_domain_data
    for fun in funs:
        ext = fun(url)
        assert expected_fqdn == ext.fqdn
        assert expected_subdomain == ext.subdomain
        assert expected_domain == ext.domain
        assert expected_tld == ext.suffix
        assert expected_ip_data == ext.ipv4
        assert expected_ipv6_data == ext.ipv6


def test_american() -> None:
    """Test a common suffix, .com."""
    assert_extract("http://www.google.com", ("www.google.com", "www", "google", "com"))


def test_british() -> None:
    """Test a British suffix."""
    assert_extract(
        "http://www.theregister.co.uk",
        ("www.theregister.co.uk", "www", "theregister", "co.uk"),
    )


def test_no_subdomain() -> None:
    """Test no explicit subdomain."""
    assert_extract("http://gmail.com", ("gmail.com", "", "gmail", "com"))


def test_nested_subdomain() -> None:
    """Test multiple levels of subdomain."""
    assert_extract(
        "http://media.forums.theregister.co.uk",
        ("media.forums.theregister.co.uk", "media.forums", "theregister", "co.uk"),
    )


def test_odd_but_possible() -> None:
    """Test an odd but possible use of the common .com suffix."""
    assert_extract("http://www.www.com", ("www.www.com", "www", "www", "com"))
    assert_extract("http://www.com", ("www.com", "", "www", "com"))


def test_suffix() -> None:
    """Test strings that only contain a suffix, until the point they contain more components."""
    assert_extract("com", ("", "", "", "com"))
    assert_extract("co.uk", ("", "", "", "co.uk"))
    assert_extract("example.ck", ("", "", "", "example.ck"))
    assert_extract("www.example.ck", ("www.example.ck", "", "www", "example.ck"))
    assert_extract(
        "sub.www.example.ck", ("sub.www.example.ck", "sub", "www", "example.ck")
    )
    assert_extract("www.ck", ("www.ck", "", "www", "ck"))
    assert_extract("nes.buskerud.no", ("", "", "", "nes.buskerud.no"))
    assert_extract("buskerud.no", ("buskerud.no", "", "buskerud", "no"))


def test_local_host() -> None:
    """Test local hostnames, i.e. no recognized public suffix."""
    assert_extract(
        "http://internalunlikelyhostname/", ("", "", "internalunlikelyhostname", "")
    )
    assert_extract(
        "http://internalunlikelyhostname.bizarre",
        ("", "internalunlikelyhostname", "bizarre", ""),
    )
    assert_extract(
        "http://internalunlikelyhostname.info/",
        ("internalunlikelyhostname.info", "", "internalunlikelyhostname", "info"),
    )
    assert_extract(
        "http://internalunlikelyhostname.information/",
        ("", "internalunlikelyhostname", "information", ""),
    )


def test_lenient_netloc() -> None:
    """Test function to leniently extract the netloc from a URL."""
    assert lenient_netloc("https://example.com.ca") == "example.com.ca"
    assert lenient_netloc("https://[example.com.ca]") == "[example.com.ca]"
    assert lenient_netloc("https://[example.com.ca]:5000") == "[example.com.ca]"
    assert (
        lenient_netloc("https://[aBcD:ef01:2345:6789:aBcD:ef01::]:5000")
        == "[aBcD:ef01:2345:6789:aBcD:ef01::]"
    )
    assert (
        lenient_netloc("https://[aBcD:ef01:2345:6789:aBcD:ef01:127.0.0.1]:5000")
        == "[aBcD:ef01:2345:6789:aBcD:ef01:127.0.0.1]"
    )
    assert (
        lenient_netloc(
            "https://[aBcD:ef01:2345:6789:aBcD:ef01:127\uff0e0\u30020\uff611]:5000"
        )
        == "[aBcD:ef01:2345:6789:aBcD:ef01:127\uff0e0\u30020\uff611]"
    )


@pytest.mark.skipif(not inet_pton, reason="inet_pton unavailable")
def test_looks_like_ip_with_inet_pton() -> None:
    """Test preferred function to check if a string looks like an IP address."""
    assert looks_like_ip("1.1.1.1", inet_pton) is True
    assert looks_like_ip("a.1.1.1", inet_pton) is False
    assert looks_like_ip("1.1.1.1\n", inet_pton) is False
    assert looks_like_ip("256.256.256.256", inet_pton) is False


def test_looks_like_ip_without_inet_pton() -> None:
    """Test fallback function to check if a string looks like an IP address."""
    assert looks_like_ip("1.1.1.1", None) is True
    assert looks_like_ip("a.1.1.1", None) is False
    assert looks_like_ip("1.1.1.1\n", None) is False
    assert looks_like_ip("256.256.256.256", None) is False


def test_similar_to_ip() -> None:
    """Test strings that look like IP addresses but are not."""
    assert_extract("1\xe9", ("", "", "1\xe9", ""))
    assert_extract("1.1.1.1\ncom", ("", "1.1.1", "1\ncom", ""))
    assert_extract("1.1.1.1\rcom", ("", "1.1.1", "1\rcom", ""))


def test_punycode() -> None:
    """Test URLs with Punycode."""
    assert_extract(
        "http://xn--h1alffa9f.xn--p1ai",
        ("xn--h1alffa9f.xn--p1ai", "", "xn--h1alffa9f", "xn--p1ai"),
    )
    assert_extract(
        "http://xN--h1alffa9f.xn--p1ai",
        ("xN--h1alffa9f.xn--p1ai", "", "xN--h1alffa9f", "xn--p1ai"),
    )
    assert_extract(
        "http://XN--h1alffa9f.xn--p1ai",
        ("XN--h1alffa9f.xn--p1ai", "", "XN--h1alffa9f", "xn--p1ai"),
    )
    # Entries that might generate UnicodeError exception
    # This subdomain generates UnicodeError 'IDNA does not round-trip'
    assert_extract(
        "xn--tub-1m9d15sfkkhsifsbqygyujjrw602gk4li5qqk98aca0w.google.com",
        (
            "xn--tub-1m9d15sfkkhsifsbqygyujjrw602gk4li5qqk98aca0w.google.com",
            "xn--tub-1m9d15sfkkhsifsbqygyujjrw602gk4li5qqk98aca0w",
            "google",
            "com",
        ),
    )
    # This subdomain generates UnicodeError 'incomplete punycode string'
    assert_extract(
        "xn--tub-1m9d15sfkkhsifsbqygyujjrw60.google.com",
        (
            "xn--tub-1m9d15sfkkhsifsbqygyujjrw60.google.com",
            "xn--tub-1m9d15sfkkhsifsbqygyujjrw60",
            "google",
            "com",
        ),
    )


def test_invalid_puny_with_puny() -> None:
    """Test URLs with a mix of in/valid Punycode."""
    assert_extract(
        "http://xn--zckzap6140b352by.blog.so-net.xn--wcvs22d.hk",
        (
            "xn--zckzap6140b352by.blog.so-net.xn--wcvs22d.hk",
            "xn--zckzap6140b352by.blog",
            "so-net",
            "xn--wcvs22d.hk",
        ),
    )
    assert_extract(
        "http://xn--&.so-net.com", ("xn--&.so-net.com", "xn--&", "so-net", "com")
    )


def test_invalid_puny_with_nonpuny() -> None:
    """Test URLs with a mix of invalid Punycode and non-Punycode."""
    assert_extract("xn--ß‌꫶ᢥ.com", ("xn--ß‌꫶ᢥ.com", "", "xn--ß‌꫶ᢥ", "com"))


def test_puny_with_non_puny() -> None:
    """Test URLs with a mix of in/valid Punycode."""
    assert_extract(
        "http://xn--zckzap6140b352by.blog.so-net.教育.hk",
        (
            "xn--zckzap6140b352by.blog.so-net.教育.hk",
            "xn--zckzap6140b352by.blog",
            "so-net",
            "教育.hk",
        ),
    )


def test_idna_2008() -> None:
    """Test that this project relies on the IDNA library.

    Python's standard library supports IDNA 2003. The IDNA 3rd party library
    adds 2008 support for characters like ß.
    """
    assert_extract(
        "xn--gieen46ers-73a.de",
        ("xn--gieen46ers-73a.de", "", "xn--gieen46ers-73a", "de"),
    )
    assert_extract(
        "angelinablog。com.de",
        ("angelinablog.com.de", "angelinablog", "com", "de"),
    )


def test_empty() -> None:
    """Test an empty URL."""
    assert_extract("http://", ("", "", "", ""))


def test_scheme() -> None:
    """Test a mix of in/valid schemes."""
    assert_extract("//", ("", "", "", ""))
    assert_extract("://", ("", "", "", ""))
    assert_extract("://example.com", ("", "", "", ""))
    assert_extract("a+-.://example.com", ("example.com", "", "example", "com"))
    assert_extract("a#//example.com", ("", "", "a", ""))
    assert_extract("a@://example.com", ("", "", "", ""))
    assert_extract("#//example.com", ("", "", "", ""))
    assert_extract(
        "https://mail.google.com/mail", ("mail.google.com", "mail", "google", "com")
    )
    assert_extract(
        "ssh://mail.google.com/mail", ("mail.google.com", "mail", "google", "com")
    )
    assert_extract(
        "//mail.google.com/mail", ("mail.google.com", "mail", "google", "com")
    )
    assert_extract(
        "mail.google.com/mail",
        ("mail.google.com", "mail", "google", "com"),
        funs=(extract,),
    )


def test_port() -> None:
    """Test a URL with a port number."""
    assert_extract(
        "git+ssh://www.github.com:8443/", ("www.github.com", "www", "github", "com")
    )


def test_username() -> None:
    """Test URLs with usernames and passwords."""
    assert_extract(
        "ftp://johndoe:5cr1p7k1dd13@1337.warez.com:2501",
        ("1337.warez.com", "1337", "warez", "com"),
    )
    assert_extract(
        "https://apple:pass@127.0.0.1:50/a",
        ("", "", "127.0.0.1", ""),
        expected_ip_data="127.0.0.1",
    )
    assert_extract(
        "https://apple:pass@[::]:50/a",
        ("", "", "[::]", ""),
        expected_ipv6_data="::",
    )
    assert_extract(
        "https://apple:pass@[aBcD:ef01:2345:6789:aBcD:ef01:127.0.0.1]:50/a",
        ("", "", "[aBcD:ef01:2345:6789:aBcD:ef01:127.0.0.1]", ""),
        expected_ipv6_data="aBcD:ef01:2345:6789:aBcD:ef01:127.0.0.1",
    )


def test_query_fragment() -> None:
    """Test URLs with query strings and fragments."""
    assert_extract("http://google.com?q=cats", ("google.com", "", "google", "com"))
    assert_extract("http://google.com#Welcome", ("google.com", "", "google", "com"))
    assert_extract("http://google.com/#Welcome", ("google.com", "", "google", "com"))
    assert_extract("http://google.com/s#Welcome", ("google.com", "", "google", "com"))
    assert_extract(
        "http://google.com/s?q=cats#Welcome", ("google.com", "", "google", "com")
    )


def test_order() -> None:
    """Test that a more-specific suffix is preferred."""
    assert_extract(
        "http://www.parliament.uk", ("www.parliament.uk", "www", "parliament", "uk")
    )
    assert_extract(
        "http://www.parliament.co.uk",
        ("www.parliament.co.uk", "www", "parliament", "co.uk"),
    )


def test_no_1st_level_tld() -> None:
    """Test a suffix without a first level, .za."""
    assert_extract("za", ("", "", "za", ""))
    assert_extract("example.za", ("", "example", "za", ""))
    assert_extract("co.za", ("", "", "", "co.za"))
    assert_extract("example.co.za", ("example.co.za", "", "example", "co.za"))
    assert_extract(
        "sub.example.co.za", ("sub.example.co.za", "sub", "example", "co.za")
    )


def test_dns_root_label() -> None:
    """Test handling a fully qualified domain name, i.e. a DNS root label, i.e. a trailing dot."""
    assert_extract(
        "http://www.example.com./", ("www.example.com", "www", "example", "com")
    )
    assert_extract(
        "http://www.example.com\u3002/", ("www.example.com", "www", "example", "com")
    )
    assert_extract(
        "http://www.example.com\uff0e/", ("www.example.com", "www", "example", "com")
    )
    assert_extract(
        "http://www.example.com\uff61/", ("www.example.com", "www", "example", "com")
    )


def test_ipv4() -> None:
    """Test IPv4 addresses."""
    assert_extract(
        "http://216.22.0.192/",
        ("", "", "216.22.0.192", ""),
        expected_ip_data="216.22.0.192",
    )
    assert_extract(
        "http://216.22.project.coop/",
        ("216.22.project.coop", "216.22", "project", "coop"),
    )
    assert_extract(
        "http://127.0.0.1/foo/bar",
        ("", "", "127.0.0.1", ""),
        expected_ip_data="127.0.0.1",
    )
    assert_extract(
        "http://127\u30020\uff0e0\uff611/foo/bar",
        ("", "", "127.0.0.1", ""),
        expected_ip_data="127.0.0.1",
    )


def test_ipv4_lookalike() -> None:
    """Test what looks like an IPv4 address, but isn't."""
    assert_extract(
        "http://256.256.256.256/foo/bar",
        ("", "256.256.256", "256", ""),
        expected_ip_data="",
    )
    assert_extract(
        "http://127.0.0/foo/bar", ("", "127.0", "0", ""), expected_ip_data=""
    )
    assert_extract(
        "http://127.0.0.0x1/foo/bar", ("", "127.0.0", "0x1", ""), expected_ip_data=""
    )
    assert_extract(
        "http://127.0.0.1.9/foo/bar", ("", "127.0.0.1", "9", ""), expected_ip_data=""
    )


def test_cache_permission(
    mocker: pytest_mock.MockerFixture, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Emit a warning once when the library can't cache the latest PSL."""
    warning = mocker.patch.object(logging.getLogger("tldextract.cache"), "warning")

    def no_permission_makedirs(*args: Any, **kwargs: Any) -> None:
        raise PermissionError(
            """[Errno 13] Permission denied:
            '/usr/local/lib/python3.11/site-packages/tldextract/.suffix_cache"""
        )

    monkeypatch.setattr(os, "makedirs", no_permission_makedirs)

    for _ in range(0, 2):
        my_extract = tldextract.TLDExtract(cache_dir=str(tmp_path))
        assert_extract(
            "http://www.google.com",
            ("www.google.com", "www", "google", "com"),
            funs=(my_extract,),
        )

    assert warning.call_count == 1
    assert warning.call_args[0][0].startswith("unable to cache")


@responses.activate
def test_cache_timeouts(tmp_path: Path) -> None:
    """Test error raised when all upstream servers time out."""
    server = "http://some-server.com"
    responses.add(responses.GET, server, status=408)
    cache = DiskCache(str(tmp_path))

    with pytest.raises(SuffixListNotFound):
        tldextract.suffix_list.find_first_response(cache, [server], 5)


def test_include_psl_private_domain_attr() -> None:
    """Test private domains, which default to not being treated differently."""
    extract_private = tldextract.TLDExtract(include_psl_private_domains=True)
    extract_public1 = tldextract.TLDExtract()
    extract_public2 = tldextract.TLDExtract(include_psl_private_domains=False)
    assert extract_private("foo.uk.com") == ExtractResult(
        subdomain="", domain="foo", suffix="uk.com", is_private=True
    )
    assert (
        extract_public1("foo.uk.com")
        == extract_public2("foo.uk.com")
        == ExtractResult(subdomain="foo", domain="uk", suffix="com", is_private=False)
    )


def test_tlds_property() -> None:
    """Test the set of suffixes when private domain extraction is un/set."""
    extract_private = tldextract.TLDExtract(
        cache_dir=None, suffix_list_urls=(), include_psl_private_domains=True
    )
    extract_public = tldextract.TLDExtract(
        cache_dir=None, suffix_list_urls=(), include_psl_private_domains=False
    )
    assert len(extract_private.tlds) > len(extract_public.tlds)


def test_global_extract() -> None:
    """Test the global, singleton, convenience interface for this library.

    Instead of constructing an instance, test that the global function exists
    and respects flags.
    """
    assert tldextract.extract(
        "blogspot.com", include_psl_private_domains=True
    ) == ExtractResult(subdomain="", domain="", suffix="blogspot.com", is_private=True)
    assert tldextract.extract(
        "foo.blogspot.com", include_psl_private_domains=True
    ) == ExtractResult(
        subdomain="", domain="foo", suffix="blogspot.com", is_private=True
    )


def test_private_domains_depth() -> None:
    """Test private domains of various depths that may also contain other private domains.

    Test how the extractions are honored with private domain extraction un/set.
    """
    assert tldextract.extract(
        "the-quick-brown-fox.ap-south-1.amazonaws.com", include_psl_private_domains=True
    ) == ExtractResult(
        subdomain="the-quick-brown-fox.ap-south-1",
        domain="amazonaws",
        suffix="com",
        is_private=False,
    )
    assert tldextract.extract(
        "ap-south-1.amazonaws.com", include_psl_private_domains=True
    ) == ExtractResult(
        subdomain="ap-south-1", domain="amazonaws", suffix="com", is_private=False
    )
    assert tldextract.extract(
        "amazonaws.com", include_psl_private_domains=True
    ) == ExtractResult(subdomain="", domain="amazonaws", suffix="com", is_private=False)
    assert tldextract.extract(
        "the-quick-brown-fox.cn-north-1.amazonaws.com.cn",
        include_psl_private_domains=True,
    ) == ExtractResult(
        subdomain="the-quick-brown-fox.cn-north-1",
        domain="amazonaws",
        suffix="com.cn",
        is_private=False,
    )
    assert tldextract.extract(
        "cn-north-1.amazonaws.com.cn", include_psl_private_domains=True
    ) == ExtractResult(
        subdomain="cn-north-1", domain="amazonaws", suffix="com.cn", is_private=False
    )
    assert tldextract.extract(
        "amazonaws.com.cn", include_psl_private_domains=True
    ) == ExtractResult(
        subdomain="", domain="amazonaws", suffix="com.cn", is_private=False
    )
    assert tldextract.extract(
        "another.icann.compute.amazonaws.com", include_psl_private_domains=True
    ) == ExtractResult(
        subdomain="",
        domain="another",
        suffix="icann.compute.amazonaws.com",
        is_private=True,
    )
    assert tldextract.extract(
        "another.s3.dualstack.us-east-1.amazonaws.com", include_psl_private_domains=True
    ) == ExtractResult(
        subdomain="",
        domain="another",
        suffix="s3.dualstack.us-east-1.amazonaws.com",
        is_private=True,
    )

    assert tldextract.extract(
        "s3.ap-south-1.amazonaws.com", include_psl_private_domains=True
    ) == ExtractResult(
        subdomain="", domain="", suffix="s3.ap-south-1.amazonaws.com", is_private=True
    )
    assert tldextract.extract(
        "s3.cn-north-1.amazonaws.com.cn", include_psl_private_domains=True
    ) == ExtractResult(
        subdomain="",
        domain="",
        suffix="s3.cn-north-1.amazonaws.com.cn",
        is_private=True,
    )
    assert tldextract.extract(
        "icann.compute.amazonaws.com", include_psl_private_domains=True
    ) == ExtractResult(
        subdomain="", domain="", suffix="icann.compute.amazonaws.com", is_private=True
    )

    # Entire URL is private suffix which ends with another private suffix
    # i.e. "s3.dualstack.us-east-1.amazonaws.com" ends with "us-east-1.amazonaws.com"
    assert tldextract.extract(
        "s3.dualstack.us-east-1.amazonaws.com", include_psl_private_domains=True
    ) == ExtractResult(
        subdomain="",
        domain="",
        suffix="s3.dualstack.us-east-1.amazonaws.com",
        is_private=True,
    )
