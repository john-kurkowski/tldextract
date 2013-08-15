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
    >>> ext.domain
    'bbc'
    >>> '.'.join(ext[:2]) # rejoin subdomain and domain
    'forums.bbc'
"""

from __future__ import with_statement

try:
    import cPickle as pickle
except ImportError:
    import pickle
import errno
from functools import wraps
import logging
from operator import itemgetter
import os
import sys
import warnings

try:
    import pkg_resources
except ImportError:
    class pkg_resources(object):
        """Fake pkg_resources interface which falls back to getting resources
        inside `tldextract`'s directory.
        """
        @classmethod
        def resource_stream(cls, package, resource_name):
            moddir = os.path.dirname(__file__)
            f = os.path.join(moddir, resource_name)
            return open(f)

import re
import socket
try: # pragma: no cover
    # Python 2
    from urllib2 import urlopen, URLError, Request
    from urlparse import scheme_chars
except ImportError: # pragma: no cover
    # Python 3
    from urllib.request import urlopen
    from urllib.error import URLError
    from urllib.parse import scheme_chars
    unicode = str

LOG = logging.getLogger("tldextract")

PUBLIC_SUFFIX_LIST_URL = 'http://mxr.mozilla.org/mozilla-central/source/netwerk/dns/effective_tld_names.dat?raw=1'

SCHEME_RE = re.compile(r'^([' + scheme_chars + ']+:)?//')
IP_RE = re.compile(r'^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$')

class ExtractResult(tuple):
    'ExtractResult(subdomain, domain, suffix)'
    __slots__ = ()
    _fields = ('subdomain', 'domain', 'suffix')

    def __new__(_cls, subdomain, domain, suffix):
        'Create new instance of ExtractResult(subdomain, domain, suffix)'
        return tuple.__new__(_cls, (subdomain, domain, suffix))

    @classmethod
    def _make(cls, iterable, new=tuple.__new__, len=len):
        'Make a new ExtractResult object from a sequence or iterable'
        result = new(cls, iterable)
        if len(result) != 3:
            raise TypeError('Expected 3 arguments, got %d' % len(result))
        return result

    def __repr__(self):
        'Return a nicely formatted representation string'
        return 'ExtractResult(subdomain=%r, domain=%r, suffix=%r)' % self

    def _asdict(self):
        'Return a new dict which maps field names to their values'
        base_zip = zip(self._fields, self)
        zipped = base_zip + [('tld', self.tld)]
        return dict(zipped)

    def _replace(_self, **kwds):
        'Return a new ExtractResult object replacing specified fields with new values'
        result = _self._make(map(kwds.pop, ('subdomain', 'domain', 'suffix'), _self))
        if kwds:
            raise ValueError('Got unexpected field names: %r' % kwds.keys())
        return result

    def __getnewargs__(self):
        'Return self as a plain tuple.  Used by copy and pickle.'
        return tuple(self)

    subdomain = property(itemgetter(0), doc='Alias for field number 0')
    domain = property(itemgetter(1), doc='Alias for field number 1')
    suffix = property(itemgetter(2), doc='Alias for field number 2')

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
    def __init__(self, fetch=True, cache_enabled=True, cache_file='',
                 suffix_list_url=PUBLIC_SUFFIX_LIST_URL,
                 fallback_to_snapshot=True,
                 debug=False):
        """
        Constructs a callable for extracting subdomain, domain, and TLD
        components from a URL.

        If fetch is True (the default) and no cached TLD set is found, this
        extractor will fetch TLD sources live over HTTP on first use. Set to
        False to not make HTTP requests. Either way, if the TLD set can't be
        read, the module will fall back to the included TLD set snapshot.

        Specifying cache_file will override the location of the TLD set.
        Defaults to /path/to/tldextract/.tld_set.

        Specifying suffix_list_url allows you to specify the location of
        the Public Suffix List file, whether on the internet ('http[s]://', etc)
        or on the local filesystem ('file://...').
        (This is a literal Public Suffix List file, not a pickled
        representation thereof.)

        By setting fallback_to_snapshot to `False`, you can be sure that
        tldextract will never fallback to a snapshot file. It will raise an
        exception if it hits that code path, in this case.
        """
        if suffix_list_url and not fetch:
            LOG.warn("You specified a suffix_list_url, but `fetch==False`. "
                     "That means tldextract will not load in the file at "
                     "that url, and the argument will have no effect. If "
                     "you want to load in from this url, set `fetch=True`. "
                     "Also note that this file is only used if a cache file "
                     "is not found, or if `cache_enabled` is `False`!  ")
        self.fetch = fetch
        self.suffix_list_url = suffix_list_url
        if cache_enabled and cache_file:
            LOG.warn("You specified a cache_file argument, but caching "
                     "is not enabled. cache_file will not be used.")
        self.cache_enabled = cache_enabled
        self.cache_file = os.path.expanduser(cache_file or
            os.environ.get("TLDEXTRACT_CACHE",
                os.path.join(os.path.dirname(__file__), '.tld_set')))
        self.fallback_to_snapshot = fallback_to_snapshot
        self.debug = debug
        self._extractor = None

    def __call__(self, url):
        """
        Takes a string URL and splits it into its subdomain, domain, and
        gTLD/ccTLD component.

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
          .rstrip(".")

        registered_domain, tld = self._get_tld_extractor().extract(netloc)
        if not tld and netloc and netloc[0].isdigit():
            try:
                is_ip = socket.inet_aton(netloc)
                return ExtractResult('', netloc, '')
            except AttributeError:
                if IP_RE.match(netloc):
                    return ExtractResult('', netloc, '')
            except socket.error:
                pass

        subdomain, _, domain = registered_domain.rpartition('.')
        return ExtractResult(subdomain, domain, tld)

    def update(self, fetch_now=False):
        if os.path.exists(self.cache_file):
            os.unlink(self.cache_file)
        self._extractor = None
        if fetch_now:
            self._get_tld_extractor()

    def _get_tld_extractor(self):
        if self._extractor:
            return self._extractor
        if self.cache_enabled:
            try:
                with open(self.cache_file) as f:
                    self._extractor = _PublicSuffixListTLDExtractor(pickle.load(f))
                    return self._extractor
            except IOError as ioe:
                file_not_found = ioe.errno == errno.ENOENT
                if not file_not_found:
                  LOG.error("error reading TLD cache file %s: %s", self.cache_file, ioe)
            except Exception as ex:
                LOG.error("error reading TLD cache file %s: %s", self.cache_file, ex)

        if self.fetch or self.suffix_list_url:
            suffix_list_source = fetch_file(self.suffix_list_url)

        tlds = get_tlds_from_suffix_list_source(suffix_list_source)
        if not tlds:
            if self.fallback_to_snapshot:
                with pkg_resources.resource_stream(__name__, '.tld_set_snapshot') as snapshot_file:
                    self._extractor = _PublicSuffixListTLDExtractor(pickle.load(snapshot_file))
                    return self._extractor
            else:
                raise Exception("tlds is empty, but fallback_to_snapshot is set"
                                " to false. Cannot proceed without tlds.")

        if self.debug:
            LOG.info("computed TLDs: [%s, ...]", ', '.join(list(tlds)[:10]))
            if LOG.isEnabledFor(logging.DEBUG):
                import difflib
                with pkg_resources.resource_stream(__name__, '.tld_set_snapshot') as snapshot_file:
                    snapshot = sorted(pickle.load(snapshot_file))
                new = sorted(tlds)
                for line in difflib.unified_diff(snapshot, new, fromfile=".tld_set_snapshot", tofile=self.cache_file):
                    if sys.version_info < (3,):
                        sys.stderr.write(line.encode('utf-8') + "\n")
                    else:
                        sys.stderr.write(line + "\n")

        if self.cache_enabled:
            try:
                with open(self.cache_file, 'wb') as f:
                    pickle.dump(tlds, f)
            except IOError as e:
                LOG.warn("unable to cache TLDs in file %s: %s", self.cache_file, e)

        self._extractor = _PublicSuffixListTLDExtractor(tlds)
        #raise Exception
        return self._extractor

TLD_EXTRACTOR = TLDExtract()

@wraps(TLD_EXTRACTOR.__call__)
def extract(url):
    return TLD_EXTRACTOR(url)

@wraps(TLD_EXTRACTOR.update)
def update(*args, **kwargs):
    return TLD_EXTRACTOR.update(*args, **kwargs)

def get_tlds_from_suffix_list_source(suffix_list_source):
    tld_finder = re.compile(r'^(?P<tld>[.*!]*\w[\S]*)', re.UNICODE | re.MULTILINE)
    tld_iter = (m.group('tld') for m in tld_finder.finditer(suffix_list_source))
    return frozenset(tld_iter)


def fetch_file(url):
    """ Fetch the file and decode it from UTF-8 encoding to Python unicode.
    """
    # NOTE: On Python 2.7.3 you get a pretty misleading, irrelevant AttributeError message bubbling
    # up from urllib2, if the `url` argument happens to be `None`. (Something about the `request`
    # object being `None`, and thus having no `timeout` attribute.) With this slightly more verbose
    # form, where you create the timeout first, the error message in this case is slightly less
    # bewildering.
    timeout = 10
    req = Request(url)
    req.timeout = timeout
    conn = urlopen(req, timeout=timeout)
    try:
        s = conn.read()
    except URLError as e:
        LOG.error(e)
        s = ''
    return _decode_utf8(s)

def _decode_utf8(s):
    """ Decode from utf8 to Python unicode string.

    The suffix list, wherever its origin, should be UTF-8 encoded.
    """
    return unicode(s, 'utf-8')


class _PublicSuffixListTLDExtractor(object):
    def __init__(self, tlds):
        self.tlds = tlds

    def extract(self, netloc):
        spl = netloc.split('.')
        lower_spl = tuple(el.lower() for el in spl)
        for i in range(len(spl)):
            maybe_tld = '.'.join(lower_spl[i:])
            exception_tld = '!' + maybe_tld
            if exception_tld in self.tlds:
                return '.'.join(spl[:i+1]), '.'.join(spl[i+1:])

            if maybe_tld in self.tlds:
                return '.'.join(spl[:i]), '.'.join(spl[i:])

            wildcard_tld = '*.' + '.'.join(lower_spl[i+1:])
            if wildcard_tld in self.tlds:
                return '.'.join(spl[:i]), '.'.join(spl[i:])

        return netloc, ''


def main():
    import argparse

    distribution = pkg_resources.get_distribution('tldextract')

    parser = argparse.ArgumentParser(
        version='%(prog)s ' + distribution.version,
        description='Parse hostname from a url or fqdn')

    parser.add_argument('input', metavar='fqdn|url',
                        type=unicode, nargs='*', help='fqdn or url')

    parser.add_argument('-u', '--update', default=False, action='store_true', help='force fetch the latest TLD definitions')
    parser.add_argument('-c', '--cache_file', help='use an alternate TLD definition file')

    args = parser.parse_args()

    if args.cache_file:
        TLD_EXTRACTOR.cache_file = args.cache_file

    if args.update:
        try:
            TLD_EXTRACTOR.update(True)
        except Exception as exc:
            sys.stderr.write(exc + "\n")
            exit(2)
    elif len(args.input) is 0:
        parser.print_usage()
        exit(1)

    for i in args.input:
        print(' '.join(extract(i)))

if __name__ == "__main__":
    main()
