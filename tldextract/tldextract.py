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

LOG = logging.getLogger(__file__)

def lreplace(subject, old, new):
    return subject[len(old):] + new if subject.startswith(old) else subject

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
    netloc = lreplace(url, "http://", "").partition("/")[0]
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
        def test_american(self):
            ext = extract("http://www.google.com")
            subdomain, domain, tld = ext['subdomain'], ext['domain'], ext['tld']
            self.assertEquals("www", subdomain)
            self.assertEquals("google", domain)
            self.assertEquals("com", tld)
            
        def test_british(self):
            ext = extract("http://www.theregister.co.uk")
            subdomain, domain, tld = ext['subdomain'], ext['domain'], ext['tld']
            self.assertEquals("www", subdomain)
            self.assertEquals("theregister", domain)
            self.assertEquals("co.uk", tld)
            
        def test_no_subdomain(self):
            ext = extract("http://gmail.com")
            subdomain, domain, tld = ext['subdomain'], ext['domain'], ext['tld']
            self.assertEquals("", subdomain)
            self.assertEquals("gmail", domain)
            self.assertEquals("com", tld)
            
        def test_nested_subdomain(self):
            ext = extract("http://media.forums.theregister.co.uk")
            subdomain, domain, tld = ext['subdomain'], ext['domain'], ext['tld']
            self.assertEquals("media.forums", subdomain)
            self.assertEquals("theregister", domain)
            self.assertEquals("co.uk", tld)

        def test_local_host(self):
            ext = extract("http://wiki/")
            self.assertFalse(ext['subdomain'])
            self.assertEquals('wiki', ext['domain'])
            self.assertFalse(ext['tld'])

        def test_qualified_local_host(self):
            ext = extract("http://wiki.info/")
            self.assertFalse(ext['subdomain'])
            self.assertEquals('wiki', ext['domain'])
            self.assertEquals('info', ext['tld'])

            ext = extract("http://wiki.information/")
            self.assertEquals('wiki', ext['subdomain'])
            self.assertEquals('information', ext['domain'])
            self.assertFalse(ext['tld'])

        def test_ip(self):
            ext = extract("http://216.22.0.192/")
            subdomain, domain, tld = ext['subdomain'], ext['domain'], ext['tld']
            self.assertFalse(subdomain)
            self.assertEquals('216.22.0.192', domain)
            self.assertFalse(tld)

            ext = extract("http://216.22.project.coop/")
            subdomain, domain, tld = ext['subdomain'], ext['domain'], ext['tld']
            self.assertEquals('216.22', subdomain)
            self.assertEquals('project', domain)
            self.assertEquals('coop', tld)

        def test_empty(self):
            ext = extract("http://")
            subdomain, domain, tld = ext['subdomain'], ext['domain'], ext['tld']
            self.assertFalse(subdomain)
            self.assertFalse(domain)
            self.assertFalse(tld)

    doctest.testmod()
    unittest.main()

