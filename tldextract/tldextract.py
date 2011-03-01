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
    >>> ext = tldextract.extract('http://forums.news.cnn.com/')
    >>> ext['subdomain'], ext['domain'], ext['tld']
    ('forums.news', 'cnn', 'com')
    >>> ext = tldextract.extract('http://forums.bbc.co.uk/')
    >>> ext['subdomain'], ext['domain'], ext['tld']
    ('forums', 'bbc', 'co.uk')
"""

from __future__ import with_statement
import codecs
import logging
import os
import re
import socket
from urllib2 import urlopen
import urlparse

LOG = logging.getLogger(__file__)

SCHEME_RE = re.compile(r'^([' + urlparse.scheme_chars + ']+:)?//')

def extract(url):
    """
    Takes a string URL and splits it into its subdomain, domain, and
    gTLD/ccTLD component.

    >>> ext = extract('http://forums.news.cnn.com/')
    >>> ext['subdomain'], ext['domain'], ext['tld']
    ('forums.news', 'cnn', 'com')
    >>> ext = extract('http://forums.bbc.co.uk/')
    >>> ext['subdomain'], ext['domain'], ext['tld']
    ('forums', 'bbc', 'co.uk')
    """
    netloc = SCHEME_RE.sub("", url).partition("/")[0].split("@")[-1].partition(':')[0]
    registered_domain, tld = netloc, ''
    m = _get_extract_tld_re().match(netloc)
    if m:
        registered_domain, tld = m.group('registered_domain'), m.group('tld')
    elif netloc and netloc[0].isdigit():
        try:
            is_ip = socket.inet_aton(netloc)
            return dict(subdomain='', domain=netloc, tld='')
        except socket.error:
            pass

    subdomain, _, domain = registered_domain.rpartition('.')
    return dict(subdomain=subdomain, domain=domain, tld=tld)

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

if __name__ == "__main__":
    import doctest
    import unittest
    from unittest import TestCase

    class ExtractTest(TestCase):
        def assertExtract(self, expected_subdomain, expected_domain, expected_tld, url):
            ext = extract(url)
            self.assertEquals(expected_subdomain, ext['subdomain'])
            self.assertEquals(expected_domain, ext['domain'])
            self.assertEquals(expected_tld, ext['tld'])
            
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

    doctest.testmod()
    unittest.main()

