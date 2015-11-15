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
"""


try:
    import cPickle as pickle
except ImportError:
    import pickle
import codecs
import collections
from contextlib import closing
import errno
from functools import wraps
import logging
import os
import re
import socket
import warnings


try:
    import pkg_resources
except ImportError:
    class pkg_resources(object): # pylint: disable=invalid-name

        """Fake pkg_resources interface which falls back to getting resources
        inside `tldextract`'s directory.
        """
        @classmethod
        def resource_stream(cls, _, resource_name):
            moddir = os.path.dirname(__file__)
            path = os.path.join(moddir, resource_name)
            return open(path)

# pylint: disable=invalid-name,undefined-variable
try:
    STRING_TYPE = basestring
except NameError:
    STRING_TYPE = str
# pylint: enable=invalid-name,undefined-variable


# pylint: disable=import-error,invalid-name,no-name-in-module,redefined-builtin
try:  # pragma: no cover
    # Python 2
    from urllib2 import urlopen
    from urlparse import scheme_chars
except ImportError:  # pragma: no cover
    # Python 3
    from urllib.request import urlopen
    from urllib.parse import scheme_chars
    unicode = str
# pylint: enable=import-error,invalid-name,no-name-in-module,redefined-builtin

LOG = logging.getLogger("tldextract")

CACHE_FILE_DEFAULT = os.path.join(os.path.dirname(__file__), '.tld_set')
CACHE_FILE = os.path.expanduser(os.environ.get("TLDEXTRACT_CACHE", CACHE_FILE_DEFAULT))

PUBLIC_SUFFIX_LIST_URLS = (
    'https://publicsuffix.org/list/public_suffix_list.dat',
    'https://raw.githubusercontent.com/publicsuffix/list/master/public_suffix_list.dat',
)

SCHEME_RE = re.compile(r'^([' + scheme_chars + ']+:)?//')
IP_RE = re.compile(r'^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$') # pylint: disable=line-too-long


class ExtractResult(collections.namedtuple('ExtractResult', 'subdomain domain suffix')):
    '''namedtuple of a URL's subdomain, domain, and suffix.'''

    # Necessary for __dict__ member to get populated in Python 3+
    __slots__ = ()

    @property
    def tld(self):
        warnings.warn('This use of tld is misleading. Use `suffix` instead.', DeprecationWarning)
        return self.suffix

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


class TLDExtract(object):
    '''A callable for extracting, subdomain, domain, and suffix components from
    a URL.'''

    # TODO: Agreed with Pylint: too-many-arguments
    def __init__(self, cache_file=CACHE_FILE, suffix_list_url=PUBLIC_SUFFIX_LIST_URLS, fetch=True, # pylint: disable=too-many-arguments
                 fallback_to_snapshot=True, include_psl_private_domains=False, extra_suffixes=None):
        """
        Constructs a callable for extracting subdomain, domain, and suffix
        components from a URL.

        Upon calling it, it first checks for a Python-pickled `cache_file`.
        By default, the `cache_file` will live in the tldextract directory.

        You can disable the caching functionality of this module  by setting `cache_file` to False.

        If the `cache_file` does not exist (such as on the first run), a live HTTP request
        will be made to obtain the data at the `suffix_list_url` -- unless `suffix_list_url`
        evaluates to `False`. Therefore you can deactivate the HTTP request functionality
        by setting this argument to `False` or `None`, like `suffix_list_url=None`.

        The default URL points to the latest version of the Mozilla Public Suffix List, but any
        similar document could be specified.

        Local files can be specified by using the `file://` protocol. (See `urllib2` documentation.)

        If there is no `cache_file` loaded and no data is found from the `suffix_list_url`,
        the module will fall back to the included TLD set snapshot. If you do not want
        this behavior, you may set `fallback_to_snapshot` to False, and an exception will be
        raised instead.

        The Public Suffix List includes a list of "private domains" as TLDs,
        such as blogspot.com. These do not fit `tldextract`'s definition of a
        suffix, so these domains are excluded by default. If you'd like them
        included instead, set `include_psl_private_domains` to True.

        You can pass additional suffixed in `extra_suffixes` argument without changing list URL
        """
        if not fetch:
            LOG.warning("The 'fetch' argument is deprecated. Instead of specifying fetch, "
                        "you should specify suffix_list_url. The equivalent of fetch=False would "
                        "be suffix_list_url=None.")
        self.suffix_list_urls = ()
        if suffix_list_url and fetch:
            if isinstance(suffix_list_url, STRING_TYPE):
                self.suffix_list_urls = (suffix_list_url,)
            else:
                # TODO: kwarg suffix_list_url can actually be a sequence of URL
                #       strings. Document this.
                self.suffix_list_urls = suffix_list_url
        self.suffix_list_urls = tuple(url.strip() for url in self.suffix_list_urls if url.strip())

        self.cache_file = os.path.expanduser(cache_file or '')
        self.fallback_to_snapshot = fallback_to_snapshot
        if not (self.suffix_list_urls or self.cache_file or self.fallback_to_snapshot):
            raise ValueError("The arguments you have provided disable all ways for tldextract "
                             "to obtain data. Please provide a suffix list data, a cache_file, "
                             "or set `fallback_to_snapshot` to `True`.")

        self.include_psl_private_domains = include_psl_private_domains
        self.extra_suffixes = extra_suffixes
        self._extractor = None

    def __call__(self, url):
        """
        Takes a string URL and splits it into its subdomain, domain, and
        suffix (effective TLD, gTLD, ccTLD, etc.) component.

        >>> extract = TLDExtract()
        >>> extract('http://forums.news.cnn.com/')
        ExtractResult(subdomain='forums.news', domain='cnn', suffix='com')
        >>> extract('http://forums.bbc.co.uk/')
        ExtractResult(subdomain='forums', domain='bbc', suffix='co.uk')
        """
        netloc = SCHEME_RE.sub("", url) \
            .partition("/")[0] \
            .partition("?")[0] \
            .partition("#")[0] \
            .split("@")[-1] \
            .partition(":")[0] \
            .strip() \
            .rstrip(".")

        labels = netloc.split(".")
        translations = []
        for label in labels:
            if label.startswith("xn--"):
                try:
                    translation = codecs.decode(label.encode('ascii'), 'idna')
                except UnicodeError:
                    translation = label
            else:
                translation = label
            translation = translation.lower()

            translations.append(translation)

        suffix_index = self._get_tld_extractor().suffix_index(translations)

        registered_domain = ".".join(labels[:suffix_index])
        tld = ".".join(labels[suffix_index:])

        if not tld and netloc and looks_like_ip(netloc):
            return ExtractResult('', netloc, '')

        subdomain, _, domain = registered_domain.rpartition('.')
        return ExtractResult(subdomain, domain, tld)

    def update(self, fetch_now=False):
        if os.path.exists(self.cache_file):
            os.unlink(self.cache_file)
        self._extractor = None
        if fetch_now:
            self._get_tld_extractor()

    @property
    def tlds(self):
        return self._get_tld_extractor().tlds

    def _get_tld_extractor(self):
        '''Get or compute this object's TLDExtractor. Looks up the TLDExtractor
        in roughly the following order, based on the settings passed to
        __init__:

        1. Memoized on `self`
        2. Local system cache file
        3. Remote PSL, over HTTP
        4. Bundled PSL snapshot file'''
        if self._extractor:
            return self._extractor

        self._extractor = self._get_cached_tld_extractor()
        if self._extractor:
            return self._extractor

        tlds = frozenset()
        if self.suffix_list_urls:
            raw_suffix_list_data = fetch_file(self.suffix_list_urls)
            tlds = get_tlds_from_raw_suffix_list_data(
                raw_suffix_list_data,
                self.include_psl_private_domains
            )

        if not tlds and self.fallback_to_snapshot:
            self._extractor = self._get_snapshot_tld_extractor()
            return self._extractor
        elif not tlds:
            raise Exception("tlds is empty, but fallback_to_snapshot is set"
                            " to false. Cannot proceed without tlds.")

        self._cache_tlds(tlds)

        self._extractor = _PublicSuffixListTLDExtractor(self._add_extra_suffixes(tlds))
        return self._extractor

    def _get_cached_tld_extractor(self):
        '''Unpickles the local TLD cache file. Returns None on IOError or other
        unpickling error, or if this object is not set to use the cache
        file.'''
        if not self.cache_file:
            return

        try:
            with open(self.cache_file, 'rb') as cache_file:
                try:
                    suffixes = pickle.load(cache_file)
                except Exception as myriad_unpickling_errors: # pylint: disable=broad-except
                    LOG.error(
                        "error reading TLD cache file %s: %s",
                        self.cache_file,
                        myriad_unpickling_errors
                    )
                else:
                    return _PublicSuffixListTLDExtractor(
                        self._add_extra_suffixes(suffixes)
                    )
        except IOError as ioe:
            file_not_found = ioe.errno == errno.ENOENT
            if not file_not_found:
                LOG.error("error reading TLD cache file %s: %s", self.cache_file, ioe)

    def _get_snapshot_tld_extractor(self):
        snapshot_stream = pkg_resources.resource_stream(__name__, '.tld_set_snapshot')
        with closing(snapshot_stream) as snapshot_file:
            return _PublicSuffixListTLDExtractor(
                self._add_extra_suffixes(pickle.load(snapshot_file))
            )

    def _cache_tlds(self, tlds):
        '''Logs a diff of the new TLDs and caches them on disk, according to
        settings passed to __init__.'''
        LOG.info("computed TLDs: [%s, ...]", ', '.join(list(tlds)[:10]))
        if LOG.isEnabledFor(logging.DEBUG):
            import difflib
            snapshot_stream = pkg_resources.resource_stream(__name__, '.tld_set_snapshot')
            with closing(snapshot_stream) as snapshot_file:
                snapshot = sorted(pickle.load(snapshot_file))
            new = sorted(tlds)
            LOG.debug('computed TLD diff:\n' + '\n'.join(difflib.unified_diff(
                snapshot,
                new,
                fromfile=".tld_set_snapshot",
                tofile=self.cache_file
            )))

        if self.cache_file:
            try:
                with open(self.cache_file, 'wb') as cache_file:
                    pickle.dump(tlds, cache_file)
            except IOError as ioe:
                LOG.warn("unable to cache TLDs in file %s: %s", self.cache_file, ioe)

    def _add_extra_suffixes(self, suffixes):
        if self.extra_suffixes:
            suffixes = set(suffixes)
            for extra_suffix in self.extra_suffixes:
                suffixes.add(extra_suffix)
            return frozenset(suffixes)
        return suffixes


TLD_EXTRACTOR = TLDExtract()


@wraps(TLD_EXTRACTOR.__call__)
def extract(url):
    return TLD_EXTRACTOR(url)


@wraps(TLD_EXTRACTOR.update)
def update(*args, **kwargs):
    return TLD_EXTRACTOR.update(*args, **kwargs)


def get_tlds_from_raw_suffix_list_data(suffix_list_source, include_psl_private_domains=False):
    if include_psl_private_domains:
        text = suffix_list_source
    else:
        text, _, _ = suffix_list_source.partition('// ===BEGIN PRIVATE DOMAINS===')

    tld_finder = re.compile(r'^(?P<tld>[.*!]*\w[\S]*)', re.UNICODE | re.MULTILINE)
    tld_iter = (m.group('tld') for m in tld_finder.finditer(text))
    return frozenset(tld_iter)


def fetch_file(urls):
    """ Decode the first successfully fetched URL, from UTF-8 encoding to
    Python unicode.
    """
    text = ''

    for url in urls:
        try:
            conn = urlopen(url)
            text = conn.read()
        except IOError as ioe:
            LOG.error('Exception reading Public Suffix List url ' + url + ' - ' + str(ioe) + '.')
        else:
            return _decode_utf8(text)

    LOG.error(
        'No Public Suffix List found. Consider using a mirror or constructing '
        'your TLDExtract with `fetch=False`.'
    )
    return unicode('')


def _decode_utf8(text):
    """ Decode from utf8 to Python unicode string.

    The suffix list, wherever its origin, should be UTF-8 encoded.
    """
    return unicode(text, 'utf-8')


class _PublicSuffixListTLDExtractor(object):

    def __init__(self, tlds):
        self.tlds = tlds

    def suffix_index(self, lower_spl):
        """Returns the index of the first suffix label.
        Returns len(spl) if no suffix is found
        """
        for i in range(len(lower_spl)):
            maybe_tld = '.'.join(lower_spl[i:])
            exception_tld = '!' + maybe_tld
            if exception_tld in self.tlds:
                return i + 1

            if maybe_tld in self.tlds:
                return i

            wildcard_tld = '*.' + '.'.join(lower_spl[i + 1:])
            if wildcard_tld in self.tlds:
                return i

        return len(lower_spl)


def looks_like_ip(maybe_ip):
    """Does the given str look like an IP address?"""
    if not maybe_ip[0].isdigit():
        return False

    try:
        socket.inet_aton(maybe_ip)
        return True
    except (AttributeError, UnicodeError):
        if IP_RE.match(maybe_ip):
            return True
    except socket.error:
        return False


def main():
    '''tldextract CLI'''
    import argparse

    logging.basicConfig()

    distribution = pkg_resources.get_distribution('tldextract')

    parser = argparse.ArgumentParser(
        description='Parse hostname from a url or fqdn')

    parser.add_argument('--version', action='version', version='%(prog)s ' + distribution.version) # pylint: disable=no-member
    parser.add_argument('input', metavar='fqdn|url',
                        type=unicode, nargs='*', help='fqdn or url')

    parser.add_argument('-u', '--update', default=False, action='store_true',
                        help='force fetch the latest TLD definitions')
    parser.add_argument('-c', '--cache_file',
                        help='use an alternate TLD definition file')
    parser.add_argument('-p', '--private_domains', default=False, action='store_true',
                        help='Include private domains')

    args = parser.parse_args()
    tld_extract = TLDExtract(include_psl_private_domains=args.private_domains)

    if args.cache_file:
        tld_extract.cache_file = args.cache_file

    if args.update:
        tld_extract.update(True)
    elif len(args.input) is 0:
        parser.print_usage()
        exit(1)

    for i in args.input:
        print(' '.join(extract(i))) # pylint: disable=superfluous-parens


if __name__ == "__main__":
    main()
