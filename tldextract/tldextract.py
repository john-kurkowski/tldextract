# -*- coding: utf-8 -*-
"""
The `tldextract` module accurately separates the gTLD and ccTLDs from the
registered domain and subdomains of a URL. For example, you may want the
'www.google' part of [http://www.google.com](http://www.google.com). This is
simple to do by splitting on the '.' and using all but the last split element,
however that will not work for URLs with arbitrary numbers of subdomains and
country codes, unless you know what all country codes look like. Think
[http://forums.bbc.co.uk](http://forums.bbc.co.uk) for example.

`tldextract` can give you the subdomains, domain, and gTLD/ccTLD component of
a URL, because it looks up--and caches locally--the currently living TLDs
according to [iana.org](http://www.iana.org).

    >>> import tldextract
    >>> tldextract.extract('http://forums.news.cnn.com/')
    ExtractResult(subdomain='forums.news', domain='cnn', tld='com')
    >>> tldextract.extract('http://forums.bbc.co.uk/')
    ExtractResult(subdomain='forums', domain='bbc', tld='co.uk')
"""

from __future__ import with_statement
import codecs
import logging
from operator import itemgetter
import os
import re
import socket
import sys
from urllib2 import urlopen
import urlparse

LOG = logging.getLogger(__file__)

SCHEME_RE = re.compile(r'^([' + urlparse.scheme_chars + ']+:)?//')
IP_RE = re.compile(r'^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$')

class ExtractResult(tuple):
    'ExtractResult(subdomain, domain, tld)' 
    __slots__ = () 
    _fields = ('subdomain', 'domain', 'tld') 

    def __new__(_cls, subdomain, domain, tld):
        return tuple.__new__(_cls, (subdomain, domain, tld)) 

    def __repr__(self):
        'Return a nicely formatted representation string'
        return 'ExtractResult(subdomain=%r, domain=%r, tld=%r)' % self 

    def _asdict(self):
        'Return a new dict which maps field names to their values'
        return dict(zip(self._fields, self)) 

    subdomain = property(itemgetter(0), doc='Alias for field number 0')
    domain = property(itemgetter(1), doc='Alias for field number 1')
    tld = property(itemgetter(2), doc='Alias for field number 2')

def extract(url):
    """
    Takes a string URL and splits it into its subdomain, domain, and
    gTLD/ccTLD component.

    >>> extract('http://forums.news.cnn.com/')
    ExtractResult(subdomain='forums.news', domain='cnn', tld='com')
    >>> extract('http://forums.bbc.co.uk/')
    ExtractResult(subdomain='forums', domain='bbc', tld='co.uk')
    """
    netloc = SCHEME_RE.sub("", url).partition("/")[0].split("@")[-1].partition(':')[0]
    registered_domain, tld = netloc, ''
    m = _get_extract_tld_re().match(netloc)
    if m:
        registered_domain, tld = m.group('registered_domain'), m.group('tld')
    elif netloc and netloc[0].isdigit():
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

EXTRACT_TLD_RE = None

def _get_extract_tld_re():
    global EXTRACT_TLD_RE
    if EXTRACT_TLD_RE:
        return EXTRACT_TLD_RE

    regex_file = os.path.join(os.path.dirname(__file__), '.tld_regex')
    try:
        with codecs.open(regex_file, encoding='utf-8') as f:
            regex = f.read().strip()
            EXTRACT_TLD_RE = re.compile(regex)
            return EXTRACT_TLD_RE
    except IOError, file_not_found:
        pass
    
    page = unicode(urlopen('http://www.iana.org/domains/root/db/').read(), 'utf-8')
    
    tld_finder = re.compile('<tr class="[^"]*iana-type-(?P<iana_type>\d+).*?<a.*?>\.(?P<tld>\S+?)</a>', re.UNICODE | re.DOTALL)
    tlds = [(m.group('tld').lower(), m.group('iana_type')) for m in tld_finder.finditer(page)]
    ccTLDs = [tld for tld, iana_type in tlds if iana_type == "1"]
    gTLDs = [tld for tld, iana_type in tlds if iana_type != "1"]
        
    special = ("co", "org", "ac")
    ccTLDs.sort(key=lambda tld: tld in special)
    ccTLDs = [
        '|'.join("%s\.%s" % (s, ccTLD) for s in special) + '|' + ccTLD
        for ccTLD in ccTLDs
    ]
    regex = r"^(?P<registered_domain>.+?)\.(?P<tld>%s)$" % ('|'.join(gTLDs + ccTLDs))

    LOG.info("computed TLD regex: %s", regex)
    
    try:
        with codecs.open(regex_file, 'w', 'utf-8') as f:
            f.write(regex + '\n')
    except IOError, e:
        LOG.warn("unable to save TLD regex file %s: %s", regex_file, e)
        
    EXTRACT_TLD_RE = re.compile(regex)
    return EXTRACT_TLD_RE

def test_suite():
    import doctest
    import unittest

    class ExtractTest(unittest.TestCase):
        def assertExtract(self, expected_subdomain, expected_domain, expected_tld, url):
            ext = extract(url)
            self.assertEquals(expected_subdomain, ext.subdomain)
            self.assertEquals(expected_domain, ext.domain)
            self.assertEquals(expected_tld, ext.tld)
            
        def test_american(self):
            self.assertExtract('www', 'google', 'com', 'http://www.google.com')
            
        def test_british(self):
            self.assertExtract("www", "theregister", "co.uk", "http://www.theregister.co.uk")
            
        def test_no_subdomain(self):
            self.assertExtract("", "gmail", "com", "http://gmail.com")
            
        def test_nested_subdomain(self):
            self.assertExtract("media.forums", "theregister", "co.uk", "http://media.forums.theregister.co.uk")

        def test_local_host(self):
            self.assertExtract('', 'wiki', '', 'http://wiki/')

        def test_qualified_local_host(self):
            self.assertExtract('', 'wiki', 'info', 'http://wiki.info/')
            self.assertExtract('wiki', 'information', '', 'http://wiki.information/')

        def test_ip(self):
            self.assertExtract('', '216.22.0.192', '', 'http://216.22.0.192/')
            self.assertExtract('216.22', 'project', 'coop', 'http://216.22.project.coop/')

        def test_empty(self):
            self.assertExtract('', '', '', 'http://')

        def test_scheme(self):
            self.assertExtract('mail', 'google', 'com', 'https://mail.google.com/mail')
            self.assertExtract('mail', 'google', 'com', 'ssh://mail.google.com/mail')
            self.assertExtract('mail', 'google', 'com', '//mail.google.com/mail')
            self.assertExtract('mail', 'google', 'com', 'mail.google.com/mail')

        def test_port(self):
            self.assertExtract('www', 'github', 'com', 'git+ssh://www.github.com:8443/')

        def test_username(self):
            self.assertExtract('1337', 'warez', 'com', 'ftp://johndoe:5cr1p7k1dd13@1337.warez.com:2501')

    return unittest.TestSuite([
        doctest.DocTestSuite(__name__),
        unittest.TestLoader().loadTestsFromTestCase(ExtractTest),
    ])

def run_tests(stream=sys.stderr):
    import unittest
    suite = test_suite()
    unittest.TextTestRunner(stream).run(suite)

if __name__ == "__main__":
    run_tests()

