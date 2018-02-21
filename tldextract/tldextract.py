# -*- coding: utf-8 -*-
"""`tldextract` accurately separates the gTLD or ccTLD (generic or country code
top-level domain) from the registered domain and subdomains of a URL.

    >>> import tldextract

    >>> tldextract.extract('http://forums.news.cnn.com/')
    ExtractResult(subdomain='forums.news', domain='cnn', suffix='com')

    >>> tldextract.extract('http://forums.bbc.co.uk/') # United Kingdom
    ExtractResult(subdomain='forums', domain='bbc', suffix='co.uk')

    >>> tldextract.extract('http://www.worldbank.org.kg/') # Kyrgyzstan
    ExtractResult(subdomain='www', domain='worldbank', suffix='org.kg')

`ExtractResult` is a namedtuple, so it's simple to access the parts you want.

    >>> ext = tldextract.extract('http://forums.bbc.co.uk')
    >>> (ext.subdomain, ext.domain, ext.suffix)
    ('forums', 'bbc', 'co.uk')
    >>> # rejoin subdomain and domain
    >>> '.'.join(ext[:2])
    'forums.bbc'
    >>> # a common alias
    >>> ext.registered_domain
    'bbc.co.uk'

Note subdomain and suffix are _optional_. Not all URL-like inputs have a
subdomain or a valid suffix.

    >>> tldextract.extract('google.com')
    ExtractResult(subdomain='', domain='google', suffix='com')

    >>> tldextract.extract('google.notavalidsuffix')
    ExtractResult(subdomain='google', domain='notavalidsuffix', suffix='')

    >>> tldextract.extract('http://127.0.0.1:8080/deployed/')
    ExtractResult(subdomain='', domain='127.0.0.1', suffix='')
"""

import collections
import logging
import os
import re
from contextlib import closing
from functools import wraps

import idna

try:
    import pkg_resources
except ImportError:
    class pkg_resources(object):  # pylint: disable=invalid-name

        """Fake pkg_resources interface which falls back to getting resources
        inside `tldextract`'s directory.
        """

        @classmethod
        def resource_stream(cls, _, resource_name):
            moddir = os.path.dirname(__file__)
            path = os.path.join(moddir, resource_name)
            return open(path)

from .remote import find_first_response
from .remote import looks_like_ip
from .remote import IP_RE
from .remote import PUNY_RE
from .remote import SCHEME_RE
from .utils import cache_to_jsonfile

# pylint: disable=invalid-name,undefined-variable
try:
    STRING_TYPE = basestring
except NameError:
    STRING_TYPE = str
# pylint: enable=invalid-name,undefined-variable


LOG = logging.getLogger("tldextract")

CACHE_DIR_DEFAULT = os.path.join(os.path.dirname(__file__), '.suffix_cache/')
CACHE_DIR = os.path.expanduser(os.environ.get("TLDEXTRACT_CACHE", CACHE_DIR_DEFAULT))
CACHE_TIMEOUT = os.environ.get('TLDEXTRACT_CACHE_TIMEOUT')

PUBLIC_SUFFIX_LIST_URLS = (
    'https://publicsuffix.org/list/public_suffix_list.dat',
    'https://raw.githubusercontent.com/publicsuffix/list/master/public_suffix_list.dat',
)

PUBLIC_SUFFIX_RE = re.compile(r'^(?P<suffix>[.*!]*\w[\S]*)', re.UNICODE | re.MULTILINE)

SOURCE_PUBLICSUFFIX_ICANN = 'publicsuffix_icann'
SOURCE_PUBLICSUFFIX_PRIVATE = 'publicsuffix_private'
SOURCE_EXTRA_SUFFIXES = 'extra_suffixes'
SOURCE_IP_ADDRESS = 'ip_address'


class ExtractResult(collections.namedtuple('ExtractResult', 'subdomain domain suffix')):
    '''namedtuple of a URL's subdomain, domain, and suffix.'''

    # Necessary for __dict__ member to get populated in Python 3+
    __slots__ = ()

    @property
    def registered_domain(self):
        """
        Joins the domain and suffix fields with a dot, if they're both set.

        >>> extract('http://forums.bbc.co.uk').registered_domain
        'bbc.co.uk'
        >>> extract('http://localhost:8080').registered_domain
        ''
        """
        if self.domain and self.suffix:
            return self.domain + '.' + self.suffix
        return ''

    @property
    def fqdn(self):
        """
        Returns a Fully Qualified Domain Name, if there is a proper domain/suffix.

        >>> extract('http://forums.bbc.co.uk/path/to/file').fqdn
        'forums.bbc.co.uk'
        >>> extract('http://localhost:8080').fqdn
        ''
        """
        if self.domain and self.suffix:
            # self is the namedtuple (subdomain domain suffix)
            return '.'.join(i for i in self if i)
        return ''

    @property
    def ipv4(self):
        """
        Returns the ipv4 if that is what the presented domain/url is

        >>> extract('http://127.0.0.1/path/to/file').ipv4
        '127.0.0.1'
        >>> extract('http://127.0.0.1.1/path/to/file').ipv4
        ''
        >>> extract('http://256.1.1.1').ipv4
        ''
        """
        if not (self.suffix or self.subdomain) and IP_RE.match(self.domain):
            return self.domain
        return ''


class TLDExtract(object):
    '''A callable for extracting, subdomain, domain, and suffix components from
    a URL.'''

    # TODO: Agreed with Pylint: too-many-arguments
    def __init__(self, cache_dir=CACHE_DIR, suffix_list_urls=PUBLIC_SUFFIX_LIST_URLS,  # pylint: disable=too-many-arguments
                 fallback_to_snapshot=True, include_psl_private_domains=False, extra_suffixes=(),
                 cache_fetch_timeout=CACHE_TIMEOUT):
        """
        Constructs a callable for extracting subdomain, domain, and suffix
        components from a URL.

        Upon calling it, it first checks for a JSON in `cache_dir`.
        By default, the `cache_dir` will live in the tldextract directory.

        You can disable the caching functionality of this module  by setting `cache_dir` to False.

        If the cached version does not exist (such as on the first run), HTTP request the URLs in
        `suffix_list_urls` in order, until one returns public suffix list data. To disable HTTP
        requests, set this to something falsy.

        The default list of URLs point to the latest version of the Mozilla Public Suffix List and
        its mirror, but any similar document could be specified.

        Local files can be specified by using the `file://` protocol. (See `urllib2` documentation.)

        If there is no cached version loaded and no data is found from the `suffix_list_urls`,
        the module will fall back to the included TLD set snapshot. If you do not want
        this behavior, you may set `fallback_to_snapshot` to False, and an exception will be
        raised instead.

        You can pass additional suffixes in `extra_suffixes` argument without changing list URL

        cache_fetch_timeout is passed unmodified to the underlying request object
        per the requests documentation here:
        http://docs.python-requests.org/en/master/user/advanced/#timeouts

        cache_fetch_timeout can also be set to a single value with the
        environment variable TLDEXTRACT_CACHE_TIMEOUT, like so:

        TLDEXTRACT_CACHE_TIMEOUT="1.2"

        When set this way, the same timeout value will be used for both connect
        and read timeouts
        """
        suffix_list_urls = suffix_list_urls or ()
        self.suffix_list_urls = tuple(url.strip() for url in suffix_list_urls if url.strip())

        self.cache_dir = os.path.expanduser(cache_dir or '')
        self.fallback_to_snapshot = fallback_to_snapshot
        if not (self.suffix_list_urls or self.cache_dir or self.fallback_to_snapshot):
            raise ValueError("The arguments you have provided disable all ways for tldextract "
                             "to obtain data. Please provide a suffix list data, a cache_dir, "
                             "or set `fallback_to_snapshot` to `True`.")

        self.include_psl_private_domains = include_psl_private_domains
        self.extra_suffixes = extra_suffixes
        self._extractor = None

        self.cache_fetch_timeout = cache_fetch_timeout
        if isinstance(self.cache_fetch_timeout, STRING_TYPE):
            self.cache_fetch_timeout = float(self.cache_fetch_timeout)

    def __call__(self, url, include_psl_private_domains=None):
        # pylint: disable=line-too-long,too-many-locals
        """
        Takes a string URL and splits it into its subdomain, domain, and
        suffix (effective TLD, gTLD, ccTLD, etc.) component.

        The Public Suffix List includes a list of "private domains" as TLDs,
        such as blogspot.com. These do not fit `tldextract`'s definition of a
        suffix, so these domains are excluded by default. If you'd like them
        included instead, set `include_psl_private_domains` to True.
        >>> extract = TLDExtract()
        >>> extract('http://forums.news.cnn.com/')
        ExtractResult(subdomain='forums.news', domain='cnn', suffix='com')
        >>> extract('http://forums.bbc.co.uk/')
        ExtractResult(subdomain='forums', domain='bbc', suffix='co.uk')
        >>> extract('http://foo.blogspot.com/', include_psl_private_domains=False)
        ExtractResult(subdomain='foo', domain='blogspot', suffix='com')
        >>> extract('http://foo.blogspot.com/', include_psl_private_domains=True)
        ExtractResult(subdomain='', domain='foo', suffix='blogspot.com')
        """
        if include_psl_private_domains is None:
            include_psl_private_domains = self.include_psl_private_domains

        netloc = SCHEME_RE.sub("", url) \
            .partition("/")[0] \
            .partition("?")[0] \
            .partition("#")[0] \
            .split("@")[-1] \
            .partition(":")[0] \
            .strip() \
            .rstrip(".")

        labels = netloc.split(".")

        def decode_punycode(label):
            if PUNY_RE.match(label):
                try:
                    return idna.decode(label.encode('ascii'))
                except UnicodeError:
                    pass
            return label

        translations = [decode_punycode(label).lower() for label in labels]
        if not include_psl_private_domains:
            excluded_list_names = [SOURCE_PUBLICSUFFIX_PRIVATE]
        else:
            excluded_list_names = []
        suffix_index, _ = self._get_tld_extractor().suffix_index(
            translations,
            excluded_list_names=excluded_list_names
        )

        registered_domain = ".".join(labels[:suffix_index])
        suffix = ".".join(labels[suffix_index:])

        if not suffix and netloc and looks_like_ip(netloc):
            return ExtractResult('', netloc, '')

        subdomain, _, domain = registered_domain.rpartition('.')
        return ExtractResult(subdomain, domain, suffix)

    def update(self, fetch_now=False):
        for root, _, files in os.walk(self.cache_dir):
            for filename in files:
                if filename.endswith('.json'):
                    os.unlink(os.path.join(root, filename))
        self._extractor = None
        if fetch_now:
            self._get_tld_extractor()

    @property
    def tlds(self):
        return self._get_tld_extractor().suffix_lists[SOURCE_PUBLICSUFFIX_PRIVATE]

    def _get_tld_extractor(self):
        '''Get or compute this object's TLDExtractor. Looks up the TLDExtractor
        in the following order, based on the settings passed to
        __init__:

        1. Memoized on `self`
        2. Local system cache file
        3. Remote PSL, over HTTP
        4. Bundled PSL snapshot file'''

        if not self._extractor:
            if self.cache_dir:
                _get_remote_suffix_list = cache_to_jsonfile(
                    path=self.cache_dir,
                    ignore_kwargs=['cache_fetch_timeout']
                )(get_remote_suffix_lists)
            else:
                _get_remote_suffix_list = get_remote_suffix_lists

            suffix_lists = _get_remote_suffix_list(
                suffix_list_sources=self.suffix_list_urls,
                cache_fetch_timeout=self.cache_fetch_timeout
            )
            suffix_count = sum([len(l) for l in suffix_lists.values()])
            if not suffix_count and self.fallback_to_snapshot:
                # use included snapshot list
                suffix_lists = self._get_snapshot_tld_extractor()

            suffix_lists[SOURCE_EXTRA_SUFFIXES] = self.extra_suffixes

            suffix_count = sum([len(l) for l in suffix_lists.values()])
            if not suffix_count:
                raise Exception("tlds is empty, but fallback_to_snapshot is set"
                                " to false. Cannot proceed without tlds.")
            self._extractor = _SuffixListTLDExtractor(suffix_lists)

        return self._extractor

    @staticmethod
    def _get_snapshot_tld_extractor():
        snapshot_stream = pkg_resources.resource_stream(__name__, '.tld_set_snapshot')
        with closing(snapshot_stream) as snapshot_file:
            return get_tlds_from_raw_suffix_list_data(snapshot_file.read().decode('utf-8'))


TLD_EXTRACTOR = TLDExtract()


@wraps(TLD_EXTRACTOR.__call__)
def extract(url, include_psl_private_domains=False):
    return TLD_EXTRACTOR(url, include_psl_private_domains=include_psl_private_domains)


@wraps(TLD_EXTRACTOR.update)
def update(*args, **kwargs):
    return TLD_EXTRACTOR.update(*args, **kwargs)


def get_tlds_from_raw_suffix_list_data(suffix_list_source):
    public_text, _, private_text = suffix_list_source.partition('// ===BEGIN PRIVATE DOMAINS===')

    icann_tlds = [m.group('suffix') for m in PUBLIC_SUFFIX_RE.finditer(public_text)]
    private_tlds = [m.group('suffix') for m in PUBLIC_SUFFIX_RE.finditer(private_text)]

    return {
        SOURCE_PUBLICSUFFIX_ICANN: icann_tlds,
        SOURCE_PUBLICSUFFIX_PRIVATE: private_tlds,
    }


def get_remote_suffix_lists(suffix_list_sources, cache_fetch_timeout):
    raw_suffix_list_data = find_first_response(suffix_list_sources, cache_fetch_timeout)
    return get_tlds_from_raw_suffix_list_data(raw_suffix_list_data)


class _SuffixListTLDExtractor(object):

    def __init__(self, suffix_lists):
        self.suffix_lists = {k: frozenset(l) for k, l in suffix_lists.items()}

    def suffix_index(self, lower_spl, excluded_list_names=()):
        """Returns the index of the first suffix label.
        Returns len(spl) if no suffix is found
        """
        usable_suffix_lists = [
            (n, l) for n, l in self.suffix_lists.items() if n not in excluded_list_names
        ]
        for i in range(len(lower_spl)):
            for source_name, suffix_list in usable_suffix_lists:
                maybe_tld = '.'.join(lower_spl[i:])
                exception_tld = '!' + maybe_tld
                if not isinstance(source_name, str):
                    source_name = source_name.encode('utf8')

                if exception_tld in suffix_list:
                    return i + 1, source_name

                if maybe_tld in suffix_list:
                    return i, source_name

                wildcard_tld = '*.' + '.'.join(lower_spl[i + 1:])
                if wildcard_tld in suffix_list:
                    return i, source_name

        return len(lower_spl), ''
