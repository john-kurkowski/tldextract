# -*- coding: utf-8 -*-
"""`tldextract` accurately separates the gTLD or ccTLD (generic or country code
top-level domain) from the registered domain and subdomains of a URL.

    >>> import tldextract
    >>> tldextract.extract('http://forums.news.cnn.com/')
    ExtractResult(subdomain='forums.news', domain='cnn', tld='com')
    >>> tldextract.extract('http://forums.bbc.co.uk/') # United Kingdom
    ExtractResult(subdomain='forums', domain='bbc', tld='co.uk')
    >>> tldextract.extract('http://www.worldbank.org.kg/') # Kyrgyzstan
    ExtractResult(subdomain='www', domain='worldbank', tld='org.kg')

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
from functools import wraps
import logging
from operator import itemgetter
import os

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
import urllib2
import urlparse
import warnings

LOG = logging.getLogger(__file__)

SCHEME_RE = re.compile(r'^([' + urlparse.scheme_chars + ']+:)?//')
IP_RE = re.compile(r'^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$')

class ExtractResult(tuple):
    'ExtractResult(subdomain, domain, tld)'
    __slots__ = ()
    _fields = ('subdomain', 'domain', 'tld')

    def __new__(_cls, subdomain, domain, tld):
        'Create new instance of ExtractResult(subdomain, domain, tld)'
        return tuple.__new__(_cls, (subdomain, domain, tld))

    @classmethod
    def _make(cls, iterable, new=tuple.__new__, len=len):
        'Make a new ExtractResult object from a sequence or iterable'
        result = new(cls, iterable)
        if len(result) != 3:
            raise TypeError('Expected 3 arguments, got %d' % len(result))
        return result

    def __repr__(self):
        'Return a nicely formatted representation string'
        return 'ExtractResult(subdomain=%r, domain=%r, tld=%r)' % self

    def _asdict(self):
        'Return a new dict which maps field names to their values'
        return dict(zip(self._fields, self))

    def _replace(_self, **kwds):
        'Return a new ExtractResult object replacing specified fields with new values'
        result = _self._make(map(kwds.pop, ('subdomain', 'domain', 'tld'), _self))
        if kwds:
            raise ValueError('Got unexpected field names: %r' % kwds.keys())
        return result

    def __getnewargs__(self):
        'Return self as a plain tuple.  Used by copy and pickle.'
        return tuple(self)

    subdomain = property(itemgetter(0), doc='Alias for field number 0')
    domain = property(itemgetter(1), doc='Alias for field number 1')
    tld = property(itemgetter(2), doc='Alias for field number 2')

class TLDExtract(object):
    def __init__(self, fetch=True, cache_file=''):
        """
        Constructs a callable for extracting subdomain, domain, and TLD
        components from a URL.

        If fetch is True (the default) and no cached TLD set is found, this
        extractor will fetch TLD sources live over HTTP on first use. Set to
        False to not make HTTP requests. Either way, if the TLD set can't be
        read, the module will fall back to the included TLD set snapshot.

        Specifying cache_file will override the location of the TLD set.
        Defaults to /path/to/tldextract/.tld_set.

        """
        self.fetch = fetch
        self.cache_file = cache_file
        self._extractor = None

    def __call__(self, url):
        """
        Takes a string URL and splits it into its subdomain, domain, and
        gTLD/ccTLD component.

        >>> extract = TLDExtract()
        >>> extract('http://forums.news.cnn.com/')
        ExtractResult(subdomain='forums.news', domain='cnn', tld='com')
        >>> extract('http://forums.bbc.co.uk/')
        ExtractResult(subdomain='forums', domain='bbc', tld='co.uk')
        """
        netloc = SCHEME_RE.sub("", url).partition("/")[0]
        return self._extract(netloc)

    def _extract(self, netloc):
        netloc = netloc.split("@")[-1].partition(':')[0]
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

    def _get_tld_extractor(self):
        if self._extractor:
            return self._extractor

        moddir = os.path.dirname(__file__)
        cached_file = self.cache_file or os.path.join(moddir, '.tld_set')
        try:
            with open(cached_file) as f:
                self._extractor = _PublicSuffixListTLDExtractor(pickle.load(f))
                return self._extractor
        except Exception, ioe:
            LOG.error("error reading TLD cache file %s: %s", cached_file, ioe)

        tlds = frozenset()
        if self.fetch:
            tld_sources = (_PublicSuffixListSource,)
            tlds = frozenset(tld for tld_source in tld_sources for tld in tld_source())

        if not tlds:
            with pkg_resources.resource_stream(__name__, '.tld_set_snapshot') as snapshot_file:
                self._extractor = _PublicSuffixListTLDExtractor(pickle.load(snapshot_file))
                return self._extractor

        LOG.info("computed TLDs: %s", tlds)
        if LOG.isEnabledFor(logging.DEBUG):
            import difflib
            with pkg_resources.resource_stream(__name__, '.tld_set_snapshot') as snapshot_file:
                snapshot = sorted(pickle.load(snapshot_file))
            new = sorted(tlds)
            for line in difflib.unified_diff(snapshot, new, fromfile=".tld_set_snapshot", tofile=cached_file):
                print >> sys.stderr, line

        try:
            with open(cached_file, 'w') as f:
                pickle.dump(tlds, f)
        except IOError, e:
            LOG.warn("unable to cache TLDs in file %s: %s", cached_file, e)

        self._extractor = _PublicSuffixListTLDExtractor(tlds)
        return self._extractor

TLD_EXTRACTOR = TLDExtract()

@wraps(TLD_EXTRACTOR.__call__)
def extract(url):
    return TLD_EXTRACTOR(url)

@wraps(TLD_EXTRACTOR.__call__)
def urlsplit(url):
    warnings.warn("Global tldextract.urlsplit function will be removed in 1.0. Call urlparse.urlsplit before calling tldextract.", DeprecationWarning)
    return TLD_EXTRACTOR(urlparse.urlsplit(url).netloc)

def _fetch_page(url):
    try:
        return unicode(urllib2.urlopen(url).read(), 'utf-8')
    except urllib2.URLError, e:
        LOG.error(e)
        return u''

def _PublicSuffixListSource():
    page = _fetch_page('http://mxr.mozilla.org/mozilla-central/source/netwerk/dns/effective_tld_names.dat?raw=1')

    tld_finder = re.compile(r'^(?P<tld>[.*!]*\w[\S]*)', re.UNICODE | re.MULTILINE)
    tlds = [m.group('tld') for m in tld_finder.finditer(page)]
    return tlds

class _PublicSuffixListTLDExtractor(object):
    def __init__(self, tlds):
        self.tlds = tlds

    def extract(self, netloc):
        spl = netloc.split('.')
        for i in range(len(spl)):
            maybe_tld = '.'.join(spl[i:])
            exception_tld = '!' + maybe_tld
            if exception_tld in self.tlds:
                return '.'.join(spl[:i+1]), '.'.join(spl[i+1:])

            wildcard_tld = '*.' + '.'.join(spl[i+1:])
            if wildcard_tld in self.tlds or maybe_tld in self.tlds:
                return '.'.join(spl[:i]), maybe_tld

        return netloc, ''

if __name__ == "__main__":
    import sys
    url = sys.argv[1]
    print ' '.join(extract(url))
