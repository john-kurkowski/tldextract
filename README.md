# tldextract

## Python Module [![PyPI version](https://badge.fury.io/py/tldextract.svg)](https://badge.fury.io/py/tldextract) [![Build Status](https://travis-ci.org/john-kurkowski/tldextract.svg?branch=master)](https://travis-ci.org/john-kurkowski/tldextract)

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
looking up the currently living ones according to [the Public Suffix List
(PSL)](http://www.publicsuffix.org). So, given a URL, it knows its subdomain
from its domain, and its domain from its country code.

```python
>>> import tldextract

>>> tldextract.extract('http://forums.news.cnn.com/')
ExtractResult(subdomain='forums.news', domain='cnn', suffix='com')

>>> tldextract.extract('http://forums.bbc.co.uk/') # United Kingdom
ExtractResult(subdomain='forums', domain='bbc', suffix='co.uk')

>>> tldextract.extract('http://www.worldbank.org.kg/') # Kyrgyzstan
ExtractResult(subdomain='www', domain='worldbank', suffix='org.kg')
```

`ExtractResult` is a namedtuple, so it's simple to access the parts you want.

```python
>>> ext = tldextract.extract('http://forums.bbc.co.uk')
>>> (ext.subdomain, ext.domain, ext.suffix)
('forums', 'bbc', 'co.uk')
>>> # rejoin subdomain and domain
>>> '.'.join(ext[:2])
'forums.bbc'
>>> # a common alias
>>> ext.registered_domain
'bbc.co.uk'
```

Note subdomain and suffix are _optional_. Not all URL-like inputs have a
subdomain or a valid suffix.

```python
>>> tldextract.extract('google.com')
ExtractResult(subdomain='', domain='google', suffix='com')

>>> tldextract.extract('google.notavalidsuffix')
ExtractResult(subdomain='google', domain='notavalidsuffix', suffix='')

>>> tldextract.extract('http://127.0.0.1:8080/deployed/')
ExtractResult(subdomain='', domain='127.0.0.1', suffix='')
```

If you want to rejoin the whole namedtuple, regardless of whether a subdomain
or suffix were found:

```python
>>> ext = tldextract.extract('http://127.0.0.1:8080/deployed/')
>>> # this has unwanted dots
>>> '.'.join(ext)
'.127.0.0.1.'
>>> # join each part only if it's truthy
>>> '.'.join(part for part in ext if part)
'127.0.0.1'
```

By default, this package supports the public ICANN TLDs and their exceptions.
You can optionally support the Public Suffix List's private domains as well.

This module started by implementing the chosen answer from [this StackOverflow question on
getting the "domain name" from a URL](http://stackoverflow.com/questions/569137/how-to-get-domain-name-from-url/569219#569219).
However, the proposed regex solution doesn't address many country codes like
com.au, or the exceptions to country codes like the registered domain
parliament.uk. The Public Suffix List does, and so does this module.

### Installation

Latest release on PyPI:

```zsh
pip install tldextract
```

Or the latest dev version:

```zsh
pip install -e 'git://github.com/john-kurkowski/tldextract.git#egg=tldextract'
```

Command-line usage, splits the url components by space:

```zsh
tldextract http://forums.bbc.co.uk
# forums bbc co.uk
```

### Note About Caching

Beware when first running the module, it updates its TLD list with a live HTTP
request. This updated TLD set is cached indefinitely in
`/path/to/tldextract/.tld_set`.

(Arguably runtime bootstrapping like that shouldn't be the default behavior,
like for production systems. But I want you to have the latest TLDs, especially
when I haven't kept this code up to date.)

To avoid this fetch or control the cache's location, use your own extract
callable by setting TLDEXTRACT_CACHE environment variable or by setting the
cache_file path in TLDExtract initialization.

```python
# extract callable that falls back to the included TLD snapshot, no live HTTP fetching
no_fetch_extract = tldextract.TLDExtract(suffix_list_urls=None)
no_fetch_extract('http://www.google.com')

# extract callable that reads/writes the updated TLD set to a different path
custom_cache_extract = tldextract.TLDExtract(cache_file='/path/to/your/cache/file')
custom_cache_extract('http://www.google.com')

# extract callable that doesn't use caching
no_cache_extract = tldextract.TLDExtract(cache_file=False)
no_cache_extract('http://www.google.com')
```

If you want to stay fresh with the TLD definitions--though they don't change
often--delete the cache file occasionally, or run

```zsh
tldextract --update
```

or:

```zsh
env TLDEXTRACT_CACHE="~/tldextract.cache" tldextract --update
```

It is also recommended to delete the file after upgrading this lib.

### Advanced Usage

#### Public vs. Private Domains

The PSL [maintains a concept of "private"
domains](https://publicsuffix.org/list/).

> PRIVATE domains are amendments submitted by the domain holder, as an
> expression of how they operate their domain security policy. … While some
> applications, such as browsers when considering cookie-setting, treat all
> entries the same, other applications may wish to treat ICANN domains and
> PRIVATE domains differently.

By default, `tldextract` treats public and private domains the same.

```python
>>> extract = tldextract.TLDExtract()
>>> extract('waiterrant.blogspot.com')
ExtractResult(subdomain='waiterrant', domain='blogspot', suffix='com')
```

The following overrides this.

```python
>>> extract = tldextract.TLDExtract(include_psl_private_domains=True)
>>> extract.update() # necessary until #66 is fixed
>>> extract('waiterrant.blogspot.com')
ExtractResult(subdomain='', domain='waiterrant', suffix='blogspot.com')
```

The thinking behind the default is, it's the more common case when people
mentally parse a URL. It doesn't assume familiarity with the PSL nor that the
PSL makes such a distinction. Note this may run counter to the default parsing
behavior of other, PSL-based libraries.

#### Specifying your own URL or file for the Suffix List data

You can specify your own input data in place of the default Mozilla Public Suffix List:

```python
extract = tldextract.TLDExtract(
    suffix_list_urls=["http://foo.bar.baz"],
    # Recommended: Specify your own cache file, to minimize ambiguities about where
    # tldextract is getting its data, or cached data, from.
    cache_file='/path/to/your/cache/file',
    fallback_to_snapshot=False)
```

The above snippet will fetch from the URL *you* specified, upon first need to download the
suffix list (i.e. if the cache_file doesn't exist).

If you want to use input data from your local filesystem, just use the `file://` protocol:

```python
extract = tldextract.TLDExtract(
    suffix_list_urls=["file://absolute/path/to/your/local/suffix/list/file"],
    cache_file='/path/to/your/cache/file',
    fallback_to_snapshot=False)
```

Use an absolute path when specifying the `suffix_list_urls` keyword argument.
`os.path` is your friend.

### FAQ

#### Can you add suffix \_\_\_\_? Can you make an exception for domain \_\_\_\_?

This project doesn't contain an actual list of public suffixes. That comes from
[the Public Suffix List (PSL)](https://publicsuffix.org/). Submit amendments there.

(In the meantime, you can tell tldextract about your exception by either
forking the PSL and using your fork in the `suffix_list_urls` param, or adding
your suffix piecemeal with the `extra_suffixes` param.)

#### If I pass an invalid URL, I still get a result, no error. What gives?

To keep `tldextract` light in LoC & overhead, and because there are plenty of
URL validators out there, this library is very lenient with input. If valid
URLs are important to you, validate them before calling `tldextract`.

This lenient stance lowers the learning curve of using the library, at the cost
of desensitizing users to the nuances of URLs. Who knows how much. But in the
future, I would consider an overhaul. For example, users could opt into
validation, either receiving exceptions or error metadata on results.

## Public API

I know it's just one method, but I've needed this functionality in a few
projects and programming languages, so I've uploaded
[`tldextract` to App Engine](http://tldextract.appspot.com/). It's there on
GAE's free pricing plan until Google cuts it off. Just hit it with
your favorite HTTP client with the URL you want parsed like so:

```zsh
curl "http://tldextract.appspot.com/api/extract?url=http://www.bbc.co.uk/foo/bar/baz.html"
# {"domain": "bbc", "subdomain": "www", "suffix": "co.uk"}
```

## Contribute

### Setting up

1. `git clone` this repository.
2. Change into the new directory.
3. `pip install tox`

Alternatively you can install `detox` instead of `tox` to run tests in parallel.

### Running the Test Suite

Run all tests against all supported Python versions:

```zsh
tox
```

Run all tests against a specific Python environment configuration:

```zsh
tox -l
tox -e py37
```
