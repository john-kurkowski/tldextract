# tldextract [![PyPI version](https://badge.fury.io/py/tldextract.svg)](https://badge.fury.io/py/tldextract) [![Build Status](https://github.com/john-kurkowski/tldextract/actions/workflows/ci.yml/badge.svg)](https://github.com/john-kurkowski/tldextract/actions/workflows/ci.yml)

`tldextract` accurately separates a URL's subdomain, domain, and public suffix,
using [the Public Suffix List (PSL)](https://publicsuffix.org).

## Why?

Extracting the "domain" from a URL is harder than it looks. Naive approaches
like splitting on dots fail for domains like `forums.bbc.co.uk` (gives "co"
instead of "bbc"). `tldextract` handles these complexities correctly.

- **New to domain parsing?** Start with the [Quick Start](#quick-start)
  tutorial.
- **Need specific solutions?** Check the [How-to Guides](#how-to-guides).
- **Want to understand how it works?** See
  [Understanding Domain Parsing](#understanding-domain-parsing).

## Quick Start

### Basic Usage

```python
>>> import tldextract

>>> tldextract.extract('http://forums.news.cnn.com/')
ExtractResult(subdomain='forums.news', domain='cnn', suffix='com', is_private=False)

>>> tldextract.extract('http://forums.bbc.co.uk/') # United Kingdom
ExtractResult(subdomain='forums', domain='bbc', suffix='co.uk', is_private=False)

>>> tldextract.extract('http://www.worldbank.org.kg/') # Kyrgyzstan
ExtractResult(subdomain='www', domain='worldbank', suffix='org.kg', is_private=False)
```

Note subdomain and suffix are _optional_. Not all URL-like inputs have a
subdomain or a valid suffix.

```python
>>> tldextract.extract('google.com')
ExtractResult(subdomain='', domain='google', suffix='com', is_private=False)

>>> tldextract.extract('google.notavalidsuffix')
ExtractResult(subdomain='google', domain='notavalidsuffix', suffix='', is_private=False)

>>> tldextract.extract('http://127.0.0.1:8080/deployed/')
ExtractResult(subdomain='', domain='127.0.0.1', suffix='', is_private=False)
```

### Working with Results

To rejoin the original hostname, if it was indeed a valid, registered hostname:

```python
>>> ext = tldextract.extract('http://forums.bbc.co.uk')
>>> ext.top_domain_under_public_suffix
'bbc.co.uk'
>>> ext.fqdn
'forums.bbc.co.uk'
```

### Command Line Interface

In addition to the Python interface, there is a command-line interface. Split
the URL components by space:

```zsh
$ tldextract 'http://forums.bbc.co.uk'
forums bbc co.uk
```

## Install

Latest release on PyPI:

```zsh
pip install tldextract
```

Or the latest dev version:

```zsh
pip install -e 'git://github.com/john-kurkowski/tldextract.git#egg=tldextract'
```

## How-to Guides

### How to manage caching

Beware when first calling `tldextract`, it updates its TLD list with a live HTTP
request. This updated TLD set is usually cached indefinitely in
`$HOME/.cache/python-tldextract`. To control the cache's location, set the
`TLDEXTRACT_CACHE` environment variable or set the `cache_dir` path when
constructing a `TLDExtract`.

**For production systems:** Consider disabling live HTTP fetching to avoid
runtime dependencies.

```python
# extract callable that falls back to the included TLD snapshot, no live HTTP fetching
no_fetch_extract = tldextract.TLDExtract(suffix_list_urls=())
no_fetch_extract('http://www.google.com')

# extract callable that reads/writes the updated TLD set to a different path
custom_cache_extract = tldextract.TLDExtract(cache_dir='/path/to/your/cache/')
custom_cache_extract('http://www.google.com')

# extract callable that doesn't use caching
no_cache_extract = tldextract.TLDExtract(cache_dir=None)
no_cache_extract('http://www.google.com')
```

### How to update TLD definitions

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

### How to validate URLs before extraction

To keep `tldextract` light in LoC & overhead, and because there are plenty of
URL validators out there, this library is very lenient with input. If valid URLs
are important to you, validate them before calling `tldextract`.

To avoid parsing a string twice, you can pass `tldextract` the output of
[`urllib.parse`](https://docs.python.org/3/library/urllib.parse.html) methods.
For example:

```python
extractor = TLDExtract()
split_url = urllib.parse.urlsplit("https://foo.bar.com:8080")
split_suffix = extractor.extract_urllib(split_url)
url_to_crawl = f"{split_url.scheme}://{split_suffix.top_domain_under_public_suffix}:{split_url.port}"
```

### How to work with URLs behind firewalls

Using your own URLs could be useful in production when you don't want the delay
with updating the suffix list on first use, or if you are behind a complex
firewall.

You can specify your own input data in place of the default Mozilla Public
Suffix List by using local files with the `file://` protocol:

```python
extract = tldextract.TLDExtract(
    suffix_list_urls=["file://" + "/absolute/path/to/your/local/suffix/list/file"],
    cache_dir='/path/to/your/cache/',
    fallback_to_snapshot=False)
```

This also works via command line update:

```zsh
tldextract --update --suffix_list_url "file:///path/to/local/file"
```

### How to handle public vs. private domains

The PSL
[maintains a concept of "private" domains](https://publicsuffix.org/list/).

> PRIVATE domains are amendments submitted by the domain holder, as an
> expression of how they operate their domain security policy. … While some
> applications, such as browsers when considering cookie-setting, treat all
> entries the same, other applications may wish to treat ICANN domains and
> PRIVATE domains differently.

By default, `tldextract` treats public and private domains the same.

```python
>>> extract = tldextract.TLDExtract()
>>> extract('waiterrant.blogspot.com')
ExtractResult(subdomain='waiterrant', domain='blogspot', suffix='com', is_private=False)
```

The following overrides this.

```python
>>> extract = tldextract.TLDExtract()
>>> extract('waiterrant.blogspot.com', include_psl_private_domains=True)
ExtractResult(subdomain='', domain='waiterrant', suffix='blogspot.com', is_private=True)
```

To change the default for all extract calls:

```python
>>> extract = tldextract.TLDExtract(include_psl_private_domains=True)
>>> extract('waiterrant.blogspot.com')
ExtractResult(subdomain='', domain='waiterrant', suffix='blogspot.com', is_private=True)
```

The thinking behind the default is, it's the more common case when people
mentally parse a domain name. It doesn't assume familiarity with the PSL nor
that the PSL makes a public/private distinction. Note this default may run
counter to the default parsing behavior of other, PSL-based libraries.

### How to use custom Public Suffix List data

You can specify your own input data in place of the default Mozilla Public
Suffix List:

```python
extract = tldextract.TLDExtract(
    suffix_list_urls=["http://foo.bar.baz"],
    # Recommended: Specify your own cache file, to minimize ambiguities about where
    # tldextract is getting its data, or cached data, from.
    cache_dir='/path/to/your/cache/',
    fallback_to_snapshot=False)
```

If the cached version of public suffix definitions doesn't exist, such as on the
first run, the above snippet will request the URLs you specified in order, and
use the first successful response.

This also works via command line update:

```zsh
tldextract --update --suffix_list_url "http://foo.bar.baz"
```

You can also specify additional suffixes in the `extra_suffixes` param. These
will be merged into whatever public suffix definitions are already in use by
`tldextract`.

```python
extract = tldextract.TLDExtract(
    extra_suffixes=["foo", "bar", "baz"])
```

## Understanding Domain Parsing

### How `tldextract` Works

Rather than juggle TLDs, gTLDs, ccTLDs, and their exceptions yourself,
`tldextract` uses the [Public Suffix List](https://publicsuffix.org) to extract
currently living public suffixes. The Public Suffix List is an open source,
cross-vendor initiative that provides an accurate list of domain name suffixes.
This same list is used by web browsers to make security decisions about domains.

### Understanding Public Suffixes

> A "public suffix" is one under which Internet users can directly register
> names.

A public suffix is also sometimes called an effective TLD (eTLD). Examples
include:

- `.com` (generic top-level domain)
- `.co.uk` (country code with subdomain)
- `.github.io` (service-specific suffix)

### Private vs Public Domains Explained

The PSL maintains a concept of "private domains" - these are domains like
"blogspot.com" where individual users can register subdomains, but they're not
true public suffixes where anyone can register a domain through a registrar.

When `include_psl_private_domains=True`, tldextract treats these private domains
as suffixes. When `False` (the default), it treats them as regular domains under
public suffixes.

## FAQ

### Can you add suffix \_\_\_\_? Can you make an exception for domain \_\_\_\_?

This project doesn't contain an actual list of public suffixes. That comes from
[the Public Suffix List (PSL)](https://publicsuffix.org/). Submit amendments
there.

In the meantime, you can tell tldextract about your exception by either forking
the PSL and using your fork in the `suffix_list_urls` param, or adding your
suffix piecemeal with the `extra_suffixes` param.

### I see my suffix in [the Public Suffix List (PSL)](https://publicsuffix.org/), but this library doesn't extract it.

Check if your suffix is in the private section of the list. See
[this documentation](#public-vs-private-domains).

### If I pass an invalid URL, I still get a result, no error. What gives?

`tldextract`'s lenient string parsing stance lowers the learning curve of using
the library, at the cost of desensitizing users to the nuances of URLs. This
could be overhauled. For example, users could opt into validation, either
receiving exceptions or error metadata on results.

See the
[How to validate URLs before extraction](#how-to-validate-urls-before-extraction)
guide for more details.

## Contribute

### Setting up

1. `git clone` this repository.
2. Change into the new directory.
3. `pip install --upgrade --editable '.[testing]'`

### Running the test suite

Run all tests against all supported Python versions:

```zsh
tox --parallel
```

Run all tests against a specific Python environment configuration:

```zsh
tox -l
tox -e py311
```

### Code Style

Automatically format all code:

```zsh
ruff format .
```

## History

This package started by implementing the chosen answer from
[this StackOverflow question on getting the "domain name" from a URL](http://stackoverflow.com/questions/569137/how-to-get-domain-name-from-url/569219#569219).
However, the proposed regex solution doesn't address many country codes like
com.au, or the exceptions to country codes like the registered domain
parliament.uk. The Public Suffix List does, and so does this package.
