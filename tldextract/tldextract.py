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

import codecs
import logging
import os
import re
import socket
from urllib2 import urlopen

LOG = logging.getLogger(__file__)

def lreplace(subject, old, new):
    if not subject.startswith(old):
        return subject
    return subject[len(old):] + new

EXTRACT_TLD_RE = None

def _extract_domain_tld(url):
    netloc = lreplace(url, "http://", "").partition("/")[0]
    
    global EXTRACT_TLD_RE
    if not EXTRACT_TLD_RE:
        EXTRACT_TLD_RE = _build_extract_tld_re()
        
    m = EXTRACT_TLD_RE.match(netloc)
    if m:
        return m.group('registered_domain'), m.group('tld')
    elif netloc[0].isdigit():
        try:
            is_ip = socket.inet_aton(netloc)
            return (netloc, '')
        except socket.error:
            pass
            
    raise ValueError("Cannot extract TLD, malformed url: " + netloc)

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
    domain, tld = _extract_domain_tld(url)
    is_ip = not tld
    if is_ip:
        return ('', domain)

    subdomain, _, domain = domain.rpartition('.')
    return dict(subdomain=subdomain, domain=domain, tld=tld)

def _build_extract_tld_re():
    global EXTRACT_TLD_RE

    regex_file = os.path.join(os.path.dirname(__file__), '.tld_regex')
    try:
        with open(regex_file) as f:
            regex = f.read().strip()
            EXTRACT_TLD_RE = re.compile(regex)
            return EXTRACT_TLD_RE
    except IOError:
        pass
    
    page = unicode(urlopen('http://www.iana.org/domains/root/db/').read(), 'utf-8')
    
    ccTLDs = []
    gTLDs = []
    tld_finder = re.compile('<tr class="[^"]*iana-type-(?P<iana_type>\d+).*?<a.*?>\.(?P<tld>\S+?)</a>', re.UNICODE | re.DOTALL)
    for m in tld_finder.finditer(page):
        tld = m.group('tld').lower()
        if m.group('iana_type') == "1":
            ccTLDs.append(tld)
        else:
            gTLDs.append(tld)
        
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
            url = "http://www.google.com"

            domain, tld = _extract_domain_tld(url)
            self.assertEquals('www.google', domain)
            self.assertEquals('com', tld)

            ext = extract(url)
            subdomain, domain, tld = ext['subdomain'], ext['domain'], ext['tld']
            self.assertEquals("www", subdomain)
            self.assertEquals("google", domain)
            self.assertEquals("com", tld)
            
        def test_british(self):
            url = "http://www.theregister.co.uk"

            domain, tld = _extract_domain_tld(url)
            self.assertEquals('www.theregister', domain)
            self.assertEquals('co.uk', tld)

            ext = extract(url)
            subdomain, domain, tld = ext['subdomain'], ext['domain'], ext['tld']
            self.assertEquals("www", subdomain)
            self.assertEquals("theregister", domain)
            self.assertEquals("co.uk", tld)
            
        def test_no_subdomain(self):
            url = "http://gmail.com"

            domain, tld = _extract_domain_tld(url)
            self.assertEquals('gmail', domain)
            self.assertEquals('com', tld)

            ext = extract(url)
            subdomain, domain, tld = ext['subdomain'], ext['domain'], ext['tld']
            self.assertEquals("", subdomain)
            self.assertEquals("gmail", domain)
            self.assertEquals("com", tld)
            
        def test_nested_subdomain(self):
            url = "http://media.forums.theregister.co.uk"

            domain, tld = _extract_domain_tld(url)
            self.assertEquals('media.forums.theregister', domain)
            self.assertEquals('co.uk', tld)

            ext = extract(url)
            subdomain, domain, tld = ext['subdomain'], ext['domain'], ext['tld']
            self.assertEquals("media.forums", subdomain)
            self.assertEquals("theregister", domain)
            self.assertEquals("co.uk", tld)

    doctest.testmod()
    unittest.main()

