# tldextract [![PyPI version](https://badge.fury.io/py/tldextract.svg)](https://badge.fury.io/py/tldextract) [![Build Status](https://github.com/john-kurkowski/tldextract/actions/workflows/ci.yml/badge.svg)](https://github.com/john-kurkowski/tldextract/actions/workflows/ci.yml)

`tldextract` accurately separates a URL's subdomain, domain, and public suffix,
using [the Public Suffix List (PSL)](https://publicsuffix.org).

**Why?** Naive URL parsing like splitting on dots fails for domains like
`forums.bbc.co.uk` (gives "co" instead of "bbc"). `tldextract` handles all the
edge cases, so you don't have to.

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

### How to configure caching and updates

By default, `tldextract` fetches the latest Public Suffix List on first use and
caches it indefinitely in `$HOME/.cache/python-tldextract`.

**For production** consider disabling live HTTP fetching:

```python
# Use only the packaged snapshot, never fetch
no_fetch_extract = tldextract.TLDExtract(suffix_list_urls=())
no_fetch_extract('http://www.google.com')
```

**Custom cache location:**

```python
# Set via environment variable
export TLDEXTRACT_CACHE="/path/to/cache"

# Or in code
custom_cache_extract = tldextract.TLDExtract(cache_dir='/path/to/cache/')
```

**Update TLD definitions:**

```zsh
# Command line
tldextract --update

# Or delete the entire cache folder
rm -rf $HOME/.cache/python-tldextract
```

### How to handle public vs private domains

The Public Suffix List distinguishes between ICANN-assigned suffixes and
privately operated ones like `blogspot.com`.

**Default behavior** (treats private suffixes as regular domains):

```python
>>> tldextract.extract('waiterrant.blogspot.com')
ExtractResult(subdomain='waiterrant', domain='blogspot', suffix='com', is_private=False)
```

**Include private domains** as suffixes:

```python
>>> extract = tldextract.TLDExtract(include_psl_private_domains=True)
>>> extract('waiterrant.blogspot.com')
ExtractResult(subdomain='', domain='waiterrant', suffix='blogspot.com', is_private=True)
```

### How to use custom suffix lists

**Local file:**

```python
extract = tldextract.TLDExtract(
    suffix_list_urls=["file:///path/to/your/list.dat"],
    cache_dir='/path/to/cache/',
    fallback_to_snapshot=False)
```

**Remote URL:**

```python
extract = tldextract.TLDExtract(
    suffix_list_urls=["https://myserver.com/suffix-list.dat"])
```

**Additional suffixes:**

```python
extract = tldextract.TLDExtract(
    extra_suffixes=["foo", "bar.baz"])
```

### How to validate URLs before extraction

`tldextract` accepts any string and is very lenient. For strict URL validation,
pre-process on your own. For example, with `urllib.parse`:

```python
from urllib.parse import urlsplit

# Validate and extract in one pass
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

`tldextract` uses the [Public Suffix List](https://publicsuffix.org), a
community-maintained list of domain suffixes. The PSL contains both:

- **Public suffixes**: Where anyone can register a domain (`.com`, `.co.uk`,
  `.org.kg`)
- **Private suffixes**: Operated by companies for customer subdomains
  (`blogspot.com`, `github.io`)

Web browsers use this same list for security decisions like cookie scoping.

"Suffix" vs "TLD": While `.com` is a top-level domain (TLD), many suffixes like
`.co.uk` are technically second-level. The PSL uses "public suffix" to cover
both.

## FAQ

### Can you add/remove suffix \_\_\_\_?

`tldextract` doesn't maintain the suffix list. Submit changes to
[the Public Suffix List](https://publicsuffix.org/submit/).

Meanwhile, use the `extra_suffixes` parameter, or fork the PSL and pass it to
this library with the `suffix_list_urls` parameter.

### My suffix is in the PSL but not extracted correctly

Check if it's in the "PRIVATE" section. See
[How to handle public vs private domains](#how-to-handle-public-vs-private-domains).

### Why does it parse invalid URLs?

`tldextract` prioritizes ease of use over strict validation. It extracts domains
from any string, even partial URLs or non-URLs. For validation, see
[How to validate URLs](#how-to-validate-urls-before-extraction).

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
