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
no_fetch_extract("http://www.google.com")
```

### How to set a custom cache location

Via environment variable:

```zsh
export TLDEXTRACT_CACHE="/path/to/cache"
```

Or in code:

```python
custom_cache_extract = tldextract.TLDExtract(cache_dir="/path/to/cache/")
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
extract("waiterrant.blogspot.com")
# ExtractResult(subdomain='', domain='waiterrant', suffix='blogspot.com', is_private=True)
```

### How to use a local suffix list

```python
extract = tldextract.TLDExtract(
    suffix_list_urls=["file:///path/to/your/list.dat"],
    cache_dir="/path/to/cache/",
    fallback_to_snapshot=False,
)
```

### How to use a remote suffix list

```python
extract = tldextract.TLDExtract(
    suffix_list_urls=["https://myserver.com/suffix-list.dat"]
)
```

### How to add extra suffixes

```python
extract = tldextract.TLDExtract(extra_suffixes=["foo", "bar.baz"])
```

### How to validate URLs before extraction

```python
from urllib.parse import urlsplit

extract = tldextract.TLDExtract()
split_url = urlsplit("https://example.com/path")
result = extract.extract_urllib(split_url)
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

### Default behavior with unlisted suffixes

Unlike the [formal PSL algorithm](https://github.com/publicsuffix/list/wiki/Format#algorithm),
`tldextract` does not apply the implicit `*` rule when no suffix matches. For an
unlisted final label, `suffix` remains empty so callers can distinguish configured
public suffixes from unknown, invalid, or internal hostnames.

### Hostname representation

`tldextract` identifies public suffix boundaries but does not validate or
canonicalize hostnames. Returned strings can retain the input's casing and its
Unicode or ASCII-compatible encoding (ACE, commonly called Punycode).
Equivalent IDNA hostnames can therefore produce textually different values even
when `tldextract` identifies the same suffix boundary.

Before using `suffix`, `fqdn`, or joined-domain properties in equality checks,
allowlists, blocklists, or other security decisions, validate and normalize
both hostnames to the same IDNA representation. IDNA defines label equivalence
in terms of A-labels. See
[RFC 5890, section 2.3.2.4](https://www.rfc-editor.org/rfc/rfc5890.html#section-2.3.2.4).

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

1. [Install uv](https://docs.astral.sh/uv/getting-started/installation/).
2. `git clone` this repository.
3. Change into the new directory.
4. `uv sync`

### Running tests

```zsh
uv run pytest          # Fast local suite
uv run tox -e py310    # Supported-version suite
uv run tox --parallel  # Full matrix
uv run ruff format .   # Format code
```

## History

This package started from a
[StackOverflow answer](http://stackoverflow.com/questions/569137/how-to-get-domain-name-from-url/569219#569219)
about regex-based domain extraction. The regex approach fails for many domains,
so this library switched to the Public Suffix List for accuracy.
