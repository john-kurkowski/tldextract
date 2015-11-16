# -*- coding: utf-8 -*-

'''Run all tldextract test cases.'''

import logging
import os
import pytest
import tempfile
import traceback

import tldextract


def _temporary_file():
    """ Make a writable temporary file and return its absolute path.
    """
    return tempfile.mkstemp()[1]


FAKE_SUFFIX_LIST_URL = "file://" + os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'fixtures/fake_suffix_list_fixture.dat'
)
EXTRA_SUFFIXES = ['foo1', 'bar1', 'baz1']

# pylint: disable=invalid-name
extract = tldextract.TLDExtract(cache_file=_temporary_file())
extract_no_cache = tldextract.TLDExtract(cache_file=False)
extract_using_real_local_suffix_list = tldextract.TLDExtract(cache_file=_temporary_file())
extract_using_real_local_suffix_list_no_cache = tldextract.TLDExtract(cache_file=False)
extract_using_fallback_to_snapshot_no_cache = tldextract.TLDExtract(
    cache_file=None,
    suffix_list_url=None
)
extract_using_fake_suffix_list = tldextract.TLDExtract(
    cache_file=_temporary_file(),
    suffix_list_url=FAKE_SUFFIX_LIST_URL
)
extract_using_fake_suffix_list_no_cache = tldextract.TLDExtract(
    cache_file=None,
    suffix_list_url=FAKE_SUFFIX_LIST_URL
)
extract_using_extra_suffixes = tldextract.TLDExtract(
    cache_file=None,
    suffix_list_url=FAKE_SUFFIX_LIST_URL,
    extra_suffixes=EXTRA_SUFFIXES
)
# pylint: enable=invalid-name


@pytest.fixture(autouse=True)
def reset_log_level():
    logging.getLogger().setLevel(logging.WARN)


# Integration Tests


def test_log_snapshot_diff():
    logging.getLogger().setLevel(logging.DEBUG)

    extractor = tldextract.TLDExtract()
    try:
        os.remove(extractor.cache_file)
    except (IOError, OSError):
        logging.warning(traceback.format_exc())

    # TODO: if .tld_set_snapshot is up to date, this won't trigger a diff
    extractor('ignore.com')


def test_bad_kwargs():
    with pytest.raises(ValueError):
        tldextract.TLDExtract(
            cache_file=False, suffix_list_url=False, fallback_to_snapshot=False
        )


def test_fetch_and_suffix_list_conflict():
    """ Make sure we support both fetch and suffix_list_url kwargs for this version.

    GitHub issue #41.
    """
    extractor = tldextract.TLDExtract(suffix_list_url='foo', fetch=False)
    assert not extractor.suffix_list_urls


# Extraction Unit Tests


def assert_extract(
        expected_subdomain,
        expected_domain,
        expected_tld,
        url,
        funs=(
            extract,
            extract_no_cache,
            extract_using_real_local_suffix_list,
            extract_using_real_local_suffix_list_no_cache,
            extract_using_fallback_to_snapshot_no_cache
        )):

    for fun in funs:
        ext = fun(url)
        assert expected_subdomain == ext.subdomain
        assert expected_domain == ext.domain
        assert expected_tld == ext.tld


def test_american():
    assert_extract('www', 'google', 'com', 'http://www.google.com')


def test_british():
    assert_extract("www", "theregister", "co.uk", "http://www.theregister.co.uk")


def test_no_subdomain():
    assert_extract("", "gmail", "com", "http://gmail.com")


def test_nested_subdomain():
    assert_extract("media.forums", "theregister", "co.uk",
                   "http://media.forums.theregister.co.uk")


def test_odd_but_possible():
    assert_extract('www', 'www', 'com', 'http://www.www.com')
    assert_extract('', 'www', 'com', 'http://www.com')


def test_local_host():
    assert_extract(
        '', 'internalunlikelyhostname', '',
        'http://internalunlikelyhostname/'
    )
    assert_extract(
        'internalunlikelyhostname', 'bizarre', '',
        'http://internalunlikelyhostname.bizarre'
    )


def test_qualified_local_host():
    assert_extract(
        '', 'internalunlikelyhostname', 'info',
        'http://internalunlikelyhostname.info/'
    )
    assert_extract(
        'internalunlikelyhostname', 'information', '',
        'http://internalunlikelyhostname.information/'
    )


def test_ip():
    assert_extract('', '216.22.0.192', '', 'http://216.22.0.192/')
    assert_extract('216.22', 'project', 'coop', 'http://216.22.project.coop/')


def test_looks_like_ip():
    assert_extract('', u'1\xe9', '', u'1\xe9')


def test_punycode():
    assert_extract(
        '', 'xn--h1alffa9f', 'xn--p1ai',
        'http://xn--h1alffa9f.xn--p1ai'
    )
    # Entries that might generate UnicodeError exception
    # This subdomain generates UnicodeError 'IDNA does not round-trip'
    assert_extract(
        'xn--tub-1m9d15sfkkhsifsbqygyujjrw602gk4li5qqk98aca0w', 'google', 'com',
        'xn--tub-1m9d15sfkkhsifsbqygyujjrw602gk4li5qqk98aca0w.google.com'
    )
    # This subdomain generates UnicodeError 'incomplete punicode string'
    assert_extract(
        'xn--tub-1m9d15sfkkhsifsbqygyujjrw60', 'google', 'com',
        'xn--tub-1m9d15sfkkhsifsbqygyujjrw60.google.com'
    )


def test_empty():
    assert_extract('', '', '', 'http://')


def test_scheme():
    assert_extract('mail', 'google', 'com', 'https://mail.google.com/mail')
    assert_extract('mail', 'google', 'com', 'ssh://mail.google.com/mail')
    assert_extract('mail', 'google', 'com', '//mail.google.com/mail')
    assert_extract('mail', 'google', 'com', 'mail.google.com/mail', funs=(extract,))


def test_port():
    assert_extract('www', 'github', 'com', 'git+ssh://www.github.com:8443/')


def test_username():
    assert_extract('1337', 'warez', 'com', 'ftp://johndoe:5cr1p7k1dd13@1337.warez.com:2501')


def test_query_fragment():
    assert_extract('', 'google', 'com', 'http://google.com?q=cats')
    assert_extract('', 'google', 'com', 'http://google.com#Welcome')
    assert_extract('', 'google', 'com', 'http://google.com/#Welcome')
    assert_extract('', 'google', 'com', 'http://google.com/s#Welcome')
    assert_extract('', 'google', 'com', 'http://google.com/s?q=cats#Welcome')


def test_regex_order():
    assert_extract('www', 'parliament', 'uk', 'http://www.parliament.uk')
    assert_extract('www', 'parliament', 'co.uk', 'http://www.parliament.co.uk')


def test_unhandled_by_iana():
    assert_extract('www', 'cgs', 'act.edu.au', 'http://www.cgs.act.edu.au/')
    assert_extract('www', 'google', 'com.au', 'http://www.google.com.au/')


def test_tld_is_a_website_too():
    assert_extract('www', 'metp', 'net.cn', 'http://www.metp.net.cn')
    # assert_extract('www', 'net', 'cn', 'http://www.net.cn') # This is unhandled by the
    # PSL. Or is it?

def test_dns_root_label():
    assert_extract('www', 'example', 'com', 'http://www.example.com./')


def test_private_domains():
    assert_extract('waiterrant', 'blogspot', 'com', 'http://waiterrant.blogspot.com')


def test_invalid_puny_with_puny():
    assert_extract(
        'xn--zckzap6140b352by.blog', 'so-net', 'xn--wcvs22d.hk',
        'http://xn--zckzap6140b352by.blog.so-net.xn--wcvs22d.hk'
    )


def test_puny_with_non_puny():
    assert_extract(
        'xn--zckzap6140b352by.blog', 'so-net', u'教育.hk',
        u'http://xn--zckzap6140b352by.blog.so-net.教育.hk'
    )


# Custom Suffix List Tests


def test_suffix_which_is_not_in_custom_list():
    for fun in (extract_using_fake_suffix_list, extract_using_fake_suffix_list_no_cache):
        result = fun("www.google.com")
        assert result.suffix == ""


def test_custom_suffixes():
    for fun in (extract_using_fake_suffix_list, extract_using_fake_suffix_list_no_cache):
        for custom_suffix in ('foo', 'bar', 'baz'):
            result = fun("www.foo.bar.baz.quux" + "." + custom_suffix)
            assert result.suffix == custom_suffix


# Extra Suffixes Tests


def test_suffix_which_is_not_in_extra_list():
    result = extract_using_extra_suffixes("www.google.com")
    assert result.suffix == ""


def test_extra_suffixes():
    for custom_suffix in EXTRA_SUFFIXES:
        netloc = "www.foo.bar.baz.quux" + "." + custom_suffix
        result = extract_using_extra_suffixes(netloc)
        assert result.suffix == custom_suffix


# _asdict Tests


def test_result_as_dict():
    result = extract(
        "http://admin:password1@www.google.com:666"
        "/secret/admin/interface?param1=42"
    )
    expected_dict = {'subdomain' : 'www',
                     'domain' : 'google',
                     'suffix' : 'com'}
    assert result._asdict() == expected_dict
