"""Main tldextract unit tests."""

import logging
import os
import tempfile
from typing import Sequence, Tuple

import pytest
import responses
import tldextract
from tldextract.cache import DiskCache
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
    expected_domain_data: Tuple[str, str, str, str],
    expected_ip_data: str = "",
    funs: Sequence[tldextract.TLDExtract] = (
        extract,
        extract_no_cache,
        extract_using_real_local_suffix_list,
        extract_using_real_local_suffix_list_no_cache,
        extract_using_fallback_to_snapshot_no_cache,
    ),
) -> None:
    """Test helper to compare all the expected and actual attributes and
    properties of an extraction. Runs the same comparison across several
    permutations of tldextract instance configurations."""
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


def test_american():
    assert_extract("http://www.google.com", ("www.google.com", "www", "google", "com"))


def test_british():
    assert_extract(
        "http://www.theregister.co.uk",
        ("www.theregister.co.uk", "www", "theregister", "co.uk"),
    )


def test_no_subdomain():
    assert_extract("http://gmail.com", ("gmail.com", "", "gmail", "com"))


def test_nested_subdomain():
    assert_extract(
        "http://media.forums.theregister.co.uk",
        ("media.forums.theregister.co.uk", "media.forums", "theregister", "co.uk"),
    )


def test_odd_but_possible():
    assert_extract("http://www.www.com", ("www.www.com", "www", "www", "com"))
    assert_extract("http://www.com", ("www.com", "", "www", "com"))


def test_suffix():
    assert_extract("com", ("", "", "", "com"))
    assert_extract("co.uk", ("", "", "", "co.uk"))


def test_local_host():
    assert_extract(
        "http://internalunlikelyhostname/", ("", "", "internalunlikelyhostname", "")
    )
    assert_extract(
        "http://internalunlikelyhostname.bizarre",
        ("", "internalunlikelyhostname", "bizarre", ""),
    )


def test_qualified_local_host():
    assert_extract(
        "http://internalunlikelyhostname.info/",
        ("internalunlikelyhostname.info", "", "internalunlikelyhostname", "info"),
    )
    assert_extract(
        "http://internalunlikelyhostname.information/",
        ("", "internalunlikelyhostname", "information", ""),
    )


def test_ip():
    assert_extract(
        "http://216.22.0.192/",
        ("", "", "216.22.0.192", ""),
        expected_ip_data="216.22.0.192",
    )
    assert_extract(
        "http://216.22.project.coop/",
        ("216.22.project.coop", "216.22", "project", "coop"),
    )


def test_looks_like_ip():
    assert_extract("1\xe9", ("", "", "1\xe9", ""))


def test_punycode():
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
    # This subdomain generates UnicodeError 'incomplete punicode string'
    assert_extract(
        "xn--tub-1m9d15sfkkhsifsbqygyujjrw60.google.com",
        (
            "xn--tub-1m9d15sfkkhsifsbqygyujjrw60.google.com",
            "xn--tub-1m9d15sfkkhsifsbqygyujjrw60",
            "google",
            "com",
        ),
    )


def test_invalid_puny_with_puny():
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


def test_puny_with_non_puny():
    assert_extract(
        "http://xn--zckzap6140b352by.blog.so-net.教育.hk",
        (
            "xn--zckzap6140b352by.blog.so-net.教育.hk",
            "xn--zckzap6140b352by.blog",
            "so-net",
            "教育.hk",
        ),
    )


def test_idna_2008():
    """Python supports IDNA 2003.
    The IDNA library adds 2008 support for characters like ß.
    """
    assert_extract(
        "xn--gieen46ers-73a.de",
        ("xn--gieen46ers-73a.de", "", "xn--gieen46ers-73a", "de"),
    )
    assert_extract(
        "angelinablog。com.de",
        ("angelinablog.com.de", "angelinablog", "com", "de"),
    )


def test_empty():
    assert_extract("http://", ("", "", "", ""))


def test_scheme():
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


def test_port():
    assert_extract(
        "git+ssh://www.github.com:8443/", ("www.github.com", "www", "github", "com")
    )


def test_username():
    assert_extract(
        "ftp://johndoe:5cr1p7k1dd13@1337.warez.com:2501",
        ("1337.warez.com", "1337", "warez", "com"),
    )


def test_query_fragment():
    assert_extract("http://google.com?q=cats", ("google.com", "", "google", "com"))
    assert_extract("http://google.com#Welcome", ("google.com", "", "google", "com"))
    assert_extract("http://google.com/#Welcome", ("google.com", "", "google", "com"))
    assert_extract("http://google.com/s#Welcome", ("google.com", "", "google", "com"))
    assert_extract(
        "http://google.com/s?q=cats#Welcome", ("google.com", "", "google", "com")
    )


def test_regex_order():
    assert_extract(
        "http://www.parliament.uk", ("www.parliament.uk", "www", "parliament", "uk")
    )
    assert_extract(
        "http://www.parliament.co.uk",
        ("www.parliament.co.uk", "www", "parliament", "co.uk"),
    )


def test_unhandled_by_iana():
    assert_extract(
        "http://www.cgs.act.edu.au/", ("www.cgs.act.edu.au", "www", "cgs", "act.edu.au")
    )
    assert_extract(
        "http://www.google.com.au/", ("www.google.com.au", "www", "google", "com.au")
    )


def test_tld_is_a_website_too():
    assert_extract(
        "http://www.metp.net.cn", ("www.metp.net.cn", "www", "metp", "net.cn")
    )
    # This is unhandled by the PSL. Or is it?
    # assert_extract(http://www.net.cn',
    #                ('www.net.cn', 'www', 'net', 'cn'))


def test_dns_root_label():
    assert_extract(
        "http://www.example.com./", ("www.example.com", "www", "example", "com")
    )


def test_private_domains():
    assert_extract(
        "http://waiterrant.blogspot.com",
        ("waiterrant.blogspot.com", "waiterrant", "blogspot", "com"),
    )


def test_ipv4():
    assert_extract(
        "http://127.0.0.1/foo/bar",
        ("", "", "127.0.0.1", ""),
        expected_ip_data="127.0.0.1",
    )


def test_ipv4_bad():
    assert_extract(
        "http://256.256.256.256/foo/bar",
        ("", "256.256.256", "256", ""),
        expected_ip_data="",
    )


def test_ipv4_lookalike():
    assert_extract(
        "http://127.0.0.1.9/foo/bar", ("", "127.0.0.1", "9", ""), expected_ip_data=""
    )


def test_result_as_dict():
    result = extract(
        "http://admin:password1@www.google.com:666" "/secret/admin/interface?param1=42"
    )
    expected_dict = {"subdomain": "www", "domain": "google", "suffix": "com"}
    assert result._asdict() == expected_dict


def test_cache_permission(mocker, monkeypatch, tmpdir):
    """Emit a warning once that this can't cache the latest PSL."""

    warning = mocker.patch.object(logging.getLogger("tldextract.cache"), "warning")

    def no_permission_makedirs(*args, **kwargs):
        raise PermissionError(
            """[Errno 13] Permission denied:
            '/usr/local/lib/python3.7/site-packages/tldextract/.suffix_cache"""
        )

    monkeypatch.setattr(os, "makedirs", no_permission_makedirs)

    for _ in range(0, 2):
        my_extract = tldextract.TLDExtract(cache_dir=tmpdir)
        assert_extract(
            "http://www.google.com",
            ("www.google.com", "www", "google", "com"),
            funs=(my_extract,),
        )

    assert warning.call_count == 1
    assert warning.call_args[0][0].startswith("unable to cache")


@responses.activate
def test_cache_timeouts(tmpdir):
    server = "http://some-server.com"
    responses.add(responses.GET, server, status=408)
    cache = DiskCache(tmpdir)

    with pytest.raises(SuffixListNotFound):
        tldextract.suffix_list.find_first_response(cache, [server], 5)


def test_tlds_property():
    extract_private = tldextract.TLDExtract(
        cache_dir=None, suffix_list_urls=(), include_psl_private_domains=True
    )
    extract_public = tldextract.TLDExtract(
        cache_dir=None, suffix_list_urls=(), include_psl_private_domains=False
    )
    assert len(extract_private.tlds) > len(extract_public.tlds)


def test_global_extract():
    assert tldextract.extract("foo.blogspot.com") == ExtractResult(
        subdomain="foo", domain="blogspot", suffix="com"
    )
    assert tldextract.extract(
        "foo.blogspot.com", include_psl_private_domains=True
    ) == ExtractResult(subdomain="", domain="foo", suffix="blogspot.com")
