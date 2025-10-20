# tldextract [![PyPI version](https://badge.fury.io/py/tldextract.svg)](https://badge.fury.io/py/tldextract) [![Build Status](https://github.com/john-kurkowski/tldextract/actions/workflows/ci.yml/badge.svg)](https://github.com/john-kurkowski/tldextract/actions/workflows/ci.yml)

`tldextract` accurately separates a URL's subdomain, domain, and public suffix,
using [the Public Suffix List (PSL)](https://publicsuffix.org).

**Why?** Naive URL parsing like splitting on dots fails for domains like
`forums.bbc.co.uk` (gives "co" instead of "bbc"). `tldextract` handles the edge
cases, so you don't have to.

## Quick Start

```python
>>> import tldextract

>>> tldextract.extract('http://forums.news.cnn.com/')
ExtractResult(subdomain='forums.news', domain='cnn', suffix='com', is_private=False)

>>> tldextract.extract('http://forums.bbc.co.uk/')
ExtractResult(subdomain='forums', domain='bbc', suffix='co.uk', is_private=False)

>>> # Access the parts you need
>>> ext = tldextract.extract('http://forums.bbc.co.uk')
>>> ext.domain
'bbc'
>>> ext.top_domain_under_public_suffix
'bbc.co.uk'
>>> ext.fqdn
'forums.bbc.co.uk'
```

## Install

```zsh
pip install tldextract
```

## How-to Guides

### How to disable HTTP suffix list fetching for production

```python
no_fetch_extract = tldextract.TLDExtract(suffix_list_urls=())
no_fetch_extract('http://www.google.com')
```

### How to set a custom cache location

Via environment variable:

```python
export TLDEXTRACT_CACHE="/path/to/cache"
```

Or in code:

```python
custom_cache_extract = tldextract.TLDExtract(cache_dir='/path/to/cache/')
```

### How to update TLD definitions

Command line:

```zsh
tldextract --update
```

Or delete the cache folder:

```zsh
rm -rf $HOME/.cache/python-tldextract
```

### How to treat private domains as suffixes

```python
extract = tldextract.TLDExtract(include_psl_private_domains=True)
extract('waiterrant.blogspot.com')
# ExtractResult(subdomain='', domain='waiterrant', suffix='blogspot.com', is_private=True)
```

### How to use a local suffix list

```python
extract = tldextract.TLDExtract(
    suffix_list_urls=["file:///path/to/your/list.dat"],
    cache_dir='/path/to/cache/',
    fallback_to_snapshot=False)
```

### How to use a remote suffix list

```python
extract = tldextract.TLDExtract(
    suffix_list_urls=["https://myserver.com/suffix-list.dat"])
```

### How to add extra suffixes

```python
extract = tldextract.TLDExtract(
    extra_suffixes=["foo", "bar.baz"])
```

### How to validate URLs before extraction

```python
from urllib.parse import urlsplit

split_url = urlsplit("https://example.com:8080/path")
result = tldextract.extract_urllib(split_url)
```

## Command Line

```zsh
$ tldextract http://forums.bbc.co.uk
forums bbc co.uk

$ tldextract --update  # Update cached suffix list
$ tldextract --help    # See all options
```

## Understanding Domain Parsing

### Public Suffix List

`tldextract` uses the [Public Suffix List](https://publicsuffix.org), a
community-maintained list of domain suffixes. The PSL contains both:

- **Public suffixes**: Where anyone can register a domain (`.com`, `.co.uk`,
  `.org.kg`)
- **Private suffixes**: Operated by companies for customer subdomains
  (`blogspot.com`, `github.io`)

Web browsers use this same list for security decisions like cookie scoping.

### Suffix vs. TLD

While `.com` is a top-level domain (TLD), many suffixes like `.co.uk` are
technically second-level. The PSL uses "public suffix" to cover both.

### Default behavior with private domains

By default, `tldextract` treats private suffixes as regular domains:

```python
>>> tldextract.extract('waiterrant.blogspot.com')
ExtractResult(subdomain='waiterrant', domain='blogspot', suffix='com', is_private=False)
```

To treat them as suffixes instead, see
[How to treat private domains as suffixes](#how-to-treat-private-domains-as-suffixes).

### Caching behavior

By default, `tldextract` fetches the latest Public Suffix List on first use and
caches it indefinitely in `$HOME/.cache/python-tldextract`.

### URL validation

`tldextract` accepts any string and is very lenient. It prioritizes ease of use
over strict validation, extracting domains from any string, even partial URLs or
non-URLs.

## FAQ

### Can you add/remove suffix \_\_\_\_?

`tldextract` doesn't maintain the suffix list. Submit changes to
[the Public Suffix List](https://publicsuffix.org/submit/).

Meanwhile, use the `extra_suffixes` parameter, or fork the PSL and pass it to
this library with the `suffix_list_urls` parameter.

### My suffix is in the PSL but not extracted correctly

Check if it's in the "PRIVATE" section. See
[How to treat private domains as suffixes](#how-to-treat-private-domains-as-suffixes).

### Why does it parse invalid URLs?

See [URL validation](#url-validation) and
[How to validate URLs before extraction](#how-to-validate-urls-before-extraction).

## Contribute

### Setting up

1. `git clone` this repository.
2. Change into the new directory.
3. `pip install --upgrade --editable '.[testing]'`

### Running tests

```zsh
tox --parallel       # Test all Python versions
tox -e py311         # Test specific Python version
ruff format .        # Format code
```

## History

This package started from a
[StackOverflow answer](http://stackoverflow.com/questions/569137/how-to-get-domain-name-from-url/569219#569219)
about regex-based domain extraction. The regex approach fails for many domains,
so this library switched to the Public Suffix List for accuracy.
