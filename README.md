# Python Module

`tldextract` accurately separates the gTLD or ccTLD (generic or country code
top-level domain) from the registered domain and subdomains of a URL. For
example, say you want just the 'google' part of 'http://www.google.com'.

*Everybody gets this wrong.* Splitting on the '.' and taking the last 2
elements goes a long way, yes, but only if you're thinking of simple e.g. .com
domains. As soon as your web crawler hits a subdomain or different country
code, that method is sunk. Think parsing
[http://forums.bbc.co.uk](http://forums.bbc.co.uk) for example: the naive
splitting method above will give you 'co' as the domain and 'uk' as the TLD,
instead of 'bbc' and 'co.uk' respectively.

`tldextract` on the other hand knows what all gTLDs and ccTLDs look like by
looking up the currently living ones on [iana.org](http://www.iana.org), so
given a URL it knows its subdomain from its domain, and its domain from its
country code.

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

This module is based on the chosen answer from [this StackOverflow question on
the matter](http://stackoverflow.com/questions/569137/how-to-get-domain-name-from-url/569219#569219).

## Installation

Latest release on PyPI:

    $ pip install tldextract 

Or the latest dev version:

    $ pip install -e git://github.com/john-kurkowski/tldextract.git#egg=tldextract

Command-line usage, splits the url components by space:

    $ python -m tldextract.tldextract http://forums.bbc.co.uk
    forums bbc co.uk

Run tests:

    $ python -m tldextract.tests.all

## How It Works

The magic splitting method is very simple. The TLDs retrived from iana.org are
combined into a very long regex you would rather not maintain yourself. That's
it.

See a sample snapshot of the regex [here](https://github.com/john-kurkowski/tldextract/blob/master/tldextract/.tld_regex_snapshot).

## Note About Caching

In order to not slam iana.org for every single extraction and app startup, the
regex is cached indefinitely in `/path/to/tldextract/.tld_regex`. If you want
to stay fresh with the TLD definitions--though they don't change often--delete
this file occasionally.

# Public API

I know it's just one method, but I've needed this functionality in a few
projects and programming languages, so I've uploaded
[`tldextract` to App Engine](http://tldextract.appspot.com/). Just hit it with
your favorite HTTP client with the URL you want parsed like so:

    $ curl "http://tldextract.appspot.com/api/extract?url=http://www.bbc.co.uk/foo/bar/baz.html"
    {"domain": "bbc", "subdomain": "www", "tld": "co.uk"}

You can also
[check the live regex on App Engine](http://tldextract.appspot.com/api/re).

