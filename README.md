# Python Module

`tldextract` accurately separates the gTLD or ccTLD (generic or country code
top-level domain) from the registered domain and subdomains of a URL. For
example, say you want just the 'google' part of 'http://www.google.com'.

*Everybody gets this wrong.* Splitting on the '.' and taking the last 2
elements goes a long way only if you're thinking of simple e.g. .com
domains. Think parsing
[http://forums.bbc.co.uk](http://forums.bbc.co.uk) for example: the naive
splitting method above will give you 'co' as the domain and 'uk' as the TLD,
instead of 'bbc' and 'co.uk' respectively.

`tldextract` on the other hand knows what all gTLDs and ccTLDs look like by
looking up the currently living ones according to
[the Public Suffix List](http://www.publicsuffix.org). So,
given a URL, it knows its subdomain from its domain, and its domain from its
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

This module started by implementing the chosen answer from [this StackOverflow question on
getting the "domain name" from a URL](http://stackoverflow.com/questions/569137/how-to-get-domain-name-from-url/569219#569219).
However, the proposed regex solution doesn't address many country codes like
com.au, or the exceptions to country codes like the registered domain
parliament.uk. The Public Suffix List does.

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

## Version History

* 0.4
    * Towards 1.0: simplified the global convenience function `tldextract.extract` to take only the `url` param. Need more control over the fetching and caching of the Public Suffix List? Construct your own extract callable: `extract = tldextract.TLDExtract(fetch=True, cache_file='/path/to/your/cache/file')`. As before, the first arg controls whether live HTTP requests will be made to get the Public Suffix List, otherwise falling back on the included [snapshot](https://github.com/john-kurkowski/tldextract/blob/master/tldextract/.tld_set_snapshot). The second arg is handy if you have limited permissions where temp files can go.
* 0.3
    * Added support for a huge class of missing TLDs (Issue #1). No more need for [IANA](http://www.iana.org).
    * If you pass `fetch=False` to `tldextract.extract`, or the connection to the Public Suffix List fails, the module will fall back on the included [snapshot](https://github.com/john-kurkowski/tldextract/blob/master/tldextract/.tld_set_snapshot).
    * Internally, to support more TLDs, switched from a very long regex to set-based lookup. Cursory `timeit` runs suggest performance is the same as v0.2, even with the 1000s of new TLDs. (Note however that module init time has gone up into the tens of milliseconds as it must unpickle the set. This could add up if you're calling the script externally.)

## Note About Caching

In order to not slam TLD sources for every single extraction and app startup, the
TLD set is cached indefinitely in `/path/to/tldextract/.tld_set`. This location
can be overridden by specifying `cache_file` in the call to
`tldextract.extract`. If you want to stay fresh with the TLD
definitions--though they don't change often--delete this file occasionally.

It is also recommended to delete this file after upgrading this lib.

# Public API

I know it's just one method, but I've needed this functionality in a few
projects and programming languages, so I've uploaded
[`tldextract` to App Engine](http://tldextract.appspot.com/). It's there on
GAE's free pricing plan until Google cuts it off. Just hit it with
your favorite HTTP client with the URL you want parsed like so:

    $ curl "http://tldextract.appspot.com/api/extract?url=http://www.bbc.co.uk/foo/bar/baz.html"
    {"domain": "bbc", "subdomain": "www", "tld": "co.uk"}

