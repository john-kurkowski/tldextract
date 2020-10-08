'tldextract helpers for testing and fetching remote resources.'

import logging
import pkgutil
import re
import sys

import requests
from requests_file import FileAdapter

# pylint: disable=invalid-name,redefined-builtin
if sys.version_info >= (3,):  # pragma: no cover
    unicode = str
# pylint: enable=invalid-name,redefined-builtin

LOG = logging.getLogger('tldextract')

PUBLIC_SUFFIX_RE = re.compile(r'^(?P<suffix>[.*!]*\w[\S]*)', re.UNICODE | re.MULTILINE)


class SuffixListNotFound(LookupError):
    pass


def find_first_response(cache, urls, cache_fetch_timeout=None):
    """ Decode the first successfully fetched URL, from UTF-8 encoding to
    Python unicode.
    """
    with requests.Session() as session:
        session.mount('file://', FileAdapter())

        for url in urls:
            try:
                return cache.fetch_url(session=session, url=url, timeout=cache_fetch_timeout)
            except requests.exceptions.RequestException:
                LOG.exception(
                    'Exception reading Public Suffix List url %s',
                    url
                )
    raise SuffixListNotFound(
        'No Public Suffix List found. Consider using a mirror or constructing '
        'your TLDExtract with `suffix_list_urls=None`.'
    )


def extract_tlds_from_suffix_list(suffix_list_text):
    public_text, _, private_text = suffix_list_text.partition('// ===BEGIN PRIVATE DOMAINS===')

    public_tlds = [m.group('suffix') for m in PUBLIC_SUFFIX_RE.finditer(public_text)]
    private_tlds = [m.group('suffix') for m in PUBLIC_SUFFIX_RE.finditer(private_text)]
    return public_tlds, private_tlds


def get_suffix_lists(cache, urls, cache_fetch_timeout, fallback_to_snapshot):
    """Fetch, parse, and cache the suffix lists"""
    try:
        public_tlds, private_tlds = cache.get(namespace="publicsuffix.org-tlds", key=urls)
    except KeyError:
        try:
            text = find_first_response(cache, urls, cache_fetch_timeout=cache_fetch_timeout)
        except SuffixListNotFound as exc:
            if fallback_to_snapshot:
                text = pkgutil.get_data('tldextract', '.tld_set_snapshot')
                if not isinstance(text, unicode):
                    text = unicode(text, 'utf-8')
            else:
                raise exc

        public_tlds, private_tlds = extract_tlds_from_suffix_list(text)
        cache.set(namespace="publicsuffix.org-tlds", key=urls, value=(public_tlds, private_tlds))

    return public_tlds, private_tlds
