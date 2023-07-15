"""`tldextract` accurately separates a URL's subdomain, domain, and public suffix.

It does this via the Public Suffix List (PSL).

    >>> import tldextract

    >>> tldextract.extract('http://forums.news.cnn.com/')
    ExtractResult(subdomain='forums.news', domain='cnn', suffix='com')

    >>> tldextract.extract('http://forums.bbc.co.uk/') # United Kingdom
    ExtractResult(subdomain='forums', domain='bbc', suffix='co.uk')

    >>> tldextract.extract('http://www.worldbank.org.kg/') # Kyrgyzstan
    ExtractResult(subdomain='www', domain='worldbank', suffix='org.kg')

`ExtractResult` is a namedtuple, so it's simple to access the parts you want.

    >>> ext = tldextract.extract('http://forums.bbc.co.uk')
    >>> (ext.subdomain, ext.domain, ext.suffix)
    ('forums', 'bbc', 'co.uk')
    >>> # rejoin subdomain and domain
    >>> '.'.join(ext[:2])
    'forums.bbc'
    >>> # a common alias
    >>> ext.registered_domain
    'bbc.co.uk'

Note subdomain and suffix are _optional_. Not all URL-like inputs have a
subdomain or a valid suffix.

    >>> tldextract.extract('google.com')
    ExtractResult(subdomain='', domain='google', suffix='com')

    >>> tldextract.extract('google.notavalidsuffix')
    ExtractResult(subdomain='google', domain='notavalidsuffix', suffix='')

    >>> tldextract.extract('http://127.0.0.1:8080/deployed/')
    ExtractResult(subdomain='', domain='127.0.0.1', suffix='')

If you want to rejoin the whole namedtuple, regardless of whether a subdomain
or suffix were found:

    >>> ext = tldextract.extract('http://127.0.0.1:8080/deployed/')
    >>> # this has unwanted dots
    >>> '.'.join(ext)
    '.127.0.0.1.'
    >>> # join part only if truthy
    >>> '.'.join(part for part in ext if part)
    '127.0.0.1'
"""

from __future__ import annotations

import logging
import os
import urllib.parse
from collections.abc import Collection, Sequence
from functools import wraps
from typing import (
    NamedTuple,
)

import idna

from .cache import DiskCache, get_cache_dir
from .remote import lenient_netloc, looks_like_ip, looks_like_ipv6
from .suffix_list import get_suffix_lists

LOG = logging.getLogger("tldextract")


CACHE_TIMEOUT = os.environ.get("TLDEXTRACT_CACHE_TIMEOUT")

PUBLIC_SUFFIX_LIST_URLS = (
    "https://publicsuffix.org/list/public_suffix_list.dat",
    "https://raw.githubusercontent.com/publicsuffix/list/master/public_suffix_list.dat",
)


class ExtractResult(NamedTuple):
    """namedtuple of a URL's subdomain, domain, and suffix."""

    subdomain: str
    domain: str
    suffix: str

    @property
    def registered_domain(self) -> str:
        """
        Joins the domain and suffix fields with a dot, if they're both set.

        >>> extract('http://forums.bbc.co.uk').registered_domain
        'bbc.co.uk'
        >>> extract('http://localhost:8080').registered_domain
        ''
        """
        if self.suffix and self.domain:
            return f"{self.domain}.{self.suffix}"
        return ""

    @property
    def fqdn(self) -> str:
        """
        Returns a Fully Qualified Domain Name, if there is a proper domain/suffix.

        >>> extract('http://forums.bbc.co.uk/path/to/file').fqdn
        'forums.bbc.co.uk'
        >>> extract('http://localhost:8080').fqdn
        ''
        """
        if self.suffix and self.domain:
            # Disable bogus lint error (https://github.com/PyCQA/pylint/issues/2568)
            # pylint: disable-next=not-an-iterable
            return ".".join(i for i in self if i)
        return ""

    @property
    def ipv4(self) -> str:
        """
        Returns the ipv4 if that is what the presented domain/url is.

        >>> extract('http://127.0.0.1/path/to/file').ipv4
        '127.0.0.1'
        >>> extract('http://127.0.0.1.1/path/to/file').ipv4
        ''
        >>> extract('http://256.1.1.1').ipv4
        ''
        """
        if (
            self.domain
            and not (self.suffix or self.subdomain)
            and looks_like_ip(self.domain)
        ):
            return self.domain
        return ""

    @property
    def ipv6(self) -> str:
        """
        Returns the ipv6 if that is what the presented domain/url is.

        >>> extract('http://[aBcD:ef01:2345:6789:aBcD:ef01:127.0.0.1]/path/to/file').ipv6
        'aBcD:ef01:2345:6789:aBcD:ef01:127.0.0.1'
        >>> extract('http://[aBcD:ef01:2345:6789:aBcD:ef01:127.0.0.1.1]/path/to/file').ipv6
        ''
        >>> extract('http://[aBcD:ef01:2345:6789:aBcD:ef01:256.0.0.1]').ipv6
        ''
        """
        min_num_ipv6_chars = 4
        if (
            len(self.domain) >= min_num_ipv6_chars
            and self.domain[0] == "["
            and self.domain[-1] == "]"
            and not (self.suffix or self.subdomain)
        ):
            debracketed = self.domain[1:-1]
            if looks_like_ipv6(debracketed):
                return debracketed
        return ""


class TLDExtract:
    """A callable for extracting, subdomain, domain, and suffix components from a URL."""

    # TODO: Agreed with Pylint: too-many-arguments
    def __init__(  # pylint: disable=too-many-arguments
        self,
        cache_dir: str | None = get_cache_dir(),
        suffix_list_urls: Sequence[str] = PUBLIC_SUFFIX_LIST_URLS,
        fallback_to_snapshot: bool = True,
        include_psl_private_domains: bool = False,
        extra_suffixes: Sequence[str] = (),
        cache_fetch_timeout: str | float | None = CACHE_TIMEOUT,
    ) -> None:
        """Construct a callable for extracting subdomain, domain, and suffix components from a URL.

        Upon calling it, it first checks for a JSON in `cache_dir`. By default,
        the `cache_dir` will live in the tldextract directory. You can disable
        the caching functionality of this module by setting `cache_dir` to `None`.

        If the cached version does not exist (such as on the first run), HTTP request the URLs in
        `suffix_list_urls` in order, until one returns public suffix list data. To disable HTTP
        requests, set this to an empty sequence.

        The default list of URLs point to the latest version of the Mozilla Public Suffix List and
        its mirror, but any similar document could be specified. Local files can be specified by
        using the `file://` protocol. (See `urllib2` documentation.)

        If there is no cached version loaded and no data is found from the `suffix_list_urls`,
        the module will fall back to the included TLD set snapshot. If you do not want
        this behavior, you may set `fallback_to_snapshot` to False, and an exception will be
        raised instead.

        The Public Suffix List includes a list of "private domains" as TLDs,
        such as blogspot.com. These do not fit `tldextract`'s definition of a
        suffix, so these domains are excluded by default. If you'd like them
        included instead, set `include_psl_private_domains` to True.

        You can pass additional suffixes in `extra_suffixes` argument without changing list URL

        cache_fetch_timeout is passed unmodified to the underlying request object
        per the requests documentation here:
        http://docs.python-requests.org/en/master/user/advanced/#timeouts

        cache_fetch_timeout can also be set to a single value with the
        environment variable TLDEXTRACT_CACHE_TIMEOUT, like so:

        TLDEXTRACT_CACHE_TIMEOUT="1.2"

        When set this way, the same timeout value will be used for both connect
        and read timeouts
        """
        suffix_list_urls = suffix_list_urls or ()
        self.suffix_list_urls = tuple(
            url.strip() for url in suffix_list_urls if url.strip()
        )

        self.fallback_to_snapshot = fallback_to_snapshot
        if not (self.suffix_list_urls or cache_dir or self.fallback_to_snapshot):
            raise ValueError(
                "The arguments you have provided disable all ways for tldextract "
                "to obtain data. Please provide a suffix list data, a cache_dir, "
                "or set `fallback_to_snapshot` to `True`."
            )

        self.include_psl_private_domains = include_psl_private_domains
        self.extra_suffixes = extra_suffixes
        self._extractor: _PublicSuffixListTLDExtractor | None = None

        self.cache_fetch_timeout = (
            float(cache_fetch_timeout)
            if isinstance(cache_fetch_timeout, str)
            else cache_fetch_timeout
        )
        self._cache = DiskCache(cache_dir)

    def __call__(
        self, url: str, include_psl_private_domains: bool | None = None
    ) -> ExtractResult:
        """Alias for `extract_str`."""
        return self.extract_str(url, include_psl_private_domains)

    def extract_str(
        self, url: str, include_psl_private_domains: bool | None = None
    ) -> ExtractResult:
        """Take a string URL and splits it into its subdomain, domain, and suffix components.

        I.e. its effective TLD, gTLD, ccTLD, etc. components.

        >>> extractor = TLDExtract()
        >>> extractor.extract_str('http://forums.news.cnn.com/')
        ExtractResult(subdomain='forums.news', domain='cnn', suffix='com')
        >>> extractor.extract_str('http://forums.bbc.co.uk/')
        ExtractResult(subdomain='forums', domain='bbc', suffix='co.uk')
        """
        return self._extract_netloc(lenient_netloc(url), include_psl_private_domains)

    def extract_urllib(
        self,
        url: urllib.parse.ParseResult | urllib.parse.SplitResult,
        include_psl_private_domains: bool | None = None,
    ) -> ExtractResult:
        """Take the output of urllib.parse URL parsing methods and further splits the parsed URL.

        Splits the parsed URL into its subdomain, domain, and suffix
        components, i.e. its effective TLD, gTLD, ccTLD, etc. components.

        This method is like `extract_str` but faster, as the string's domain
        name has already been parsed.

        >>> extractor = TLDExtract()
        >>> extractor.extract_urllib(urllib.parse.urlsplit('http://forums.news.cnn.com/'))
        ExtractResult(subdomain='forums.news', domain='cnn', suffix='com')
        >>> extractor.extract_urllib(urllib.parse.urlsplit('http://forums.bbc.co.uk/'))
        ExtractResult(subdomain='forums', domain='bbc', suffix='co.uk')
        """
        return self._extract_netloc(url.netloc, include_psl_private_domains)

    def _extract_netloc(
        self, netloc: str, include_psl_private_domains: bool | None
    ) -> ExtractResult:
        netloc_with_ascii_dots = (
            netloc.replace("\u3002", "\u002e")
            .replace("\uff0e", "\u002e")
            .replace("\uff61", "\u002e")
        )

        min_num_ipv6_chars = 4
        if (
            len(netloc_with_ascii_dots) >= min_num_ipv6_chars
            and netloc_with_ascii_dots[0] == "["
            and netloc_with_ascii_dots[-1] == "]"
        ):
            if looks_like_ipv6(netloc_with_ascii_dots[1:-1]):
                return ExtractResult("", netloc_with_ascii_dots, "")

        labels = netloc_with_ascii_dots.split(".")

        suffix_index = self._get_tld_extractor().suffix_index(
            labels, include_psl_private_domains=include_psl_private_domains
        )

        num_ipv4_labels = 4
        if suffix_index == len(labels) == num_ipv4_labels and looks_like_ip(
            netloc_with_ascii_dots
        ):
            return ExtractResult("", netloc_with_ascii_dots, "")

        suffix = ".".join(labels[suffix_index:]) if suffix_index != len(labels) else ""
        subdomain = ".".join(labels[: suffix_index - 1]) if suffix_index >= 2 else ""
        domain = labels[suffix_index - 1] if suffix_index else ""
        return ExtractResult(subdomain, domain, suffix)

    def update(self, fetch_now: bool = False) -> None:
        """Force fetch the latest suffix list definitions."""
        self._extractor = None
        self._cache.clear()
        if fetch_now:
            self._get_tld_extractor()

    @property
    def tlds(self) -> list[str]:
        """
        Returns the list of tld's used by default.

        This will vary based on `include_psl_private_domains` and `extra_suffixes`
        """
        return list(self._get_tld_extractor().tlds())

    def _get_tld_extractor(self) -> _PublicSuffixListTLDExtractor:
        """Get or compute this object's TLDExtractor.

        Looks up the TLDExtractor in roughly the following order, based on the
        settings passed to __init__:

        1. Memoized on `self`
        2. Local system _cache file
        3. Remote PSL, over HTTP
        4. Bundled PSL snapshot file
        """
        if self._extractor:
            return self._extractor

        public_tlds, private_tlds = get_suffix_lists(
            cache=self._cache,
            urls=self.suffix_list_urls,
            cache_fetch_timeout=self.cache_fetch_timeout,
            fallback_to_snapshot=self.fallback_to_snapshot,
        )

        if not any([public_tlds, private_tlds, self.extra_suffixes]):
            raise ValueError("No tlds set. Cannot proceed without tlds.")

        self._extractor = _PublicSuffixListTLDExtractor(
            public_tlds=public_tlds,
            private_tlds=private_tlds,
            extra_tlds=list(self.extra_suffixes),
            include_psl_private_domains=self.include_psl_private_domains,
        )
        return self._extractor


TLD_EXTRACTOR = TLDExtract()


class Trie:
    """Trie for storing eTLDs with their labels in reverse-order."""

    def __init__(self, matches: dict | None = None, end: bool = False) -> None:
        self.matches = matches if matches else {}
        self.end = end

    @staticmethod
    def create(suffixes: Collection[str]) -> Trie:
        """Create a Trie from a list of suffixes and return its root node."""
        root_node = Trie()

        for suffix in suffixes:
            suffix_labels = suffix.split(".")
            suffix_labels.reverse()
            root_node.add_suffix(suffix_labels)

        return root_node

    def add_suffix(self, labels: list[str]) -> None:
        """Append a suffix's labels to this Trie node."""
        node = self

        for label in labels:
            if label not in node.matches:
                node.matches[label] = Trie()
            node = node.matches[label]

        node.end = True


@wraps(TLD_EXTRACTOR.__call__)
def extract(  # pylint: disable=missing-function-docstring
    url: str, include_psl_private_domains: bool | None = False
) -> ExtractResult:
    return TLD_EXTRACTOR(url, include_psl_private_domains=include_psl_private_domains)


@wraps(TLD_EXTRACTOR.update)
def update(  # type: ignore[no-untyped-def]
    *args, **kwargs
):  # pylint: disable=missing-function-docstring
    return TLD_EXTRACTOR.update(*args, **kwargs)


class _PublicSuffixListTLDExtractor:
    """Wrapper around this project's main algo for PSL lookups."""

    def __init__(
        self,
        public_tlds: list[str],
        private_tlds: list[str],
        extra_tlds: list[str],
        include_psl_private_domains: bool = False,
    ):
        # set the default value
        self.include_psl_private_domains = include_psl_private_domains
        self.public_tlds = public_tlds
        self.private_tlds = private_tlds
        self.tlds_incl_private = frozenset(public_tlds + private_tlds + extra_tlds)
        self.tlds_excl_private = frozenset(public_tlds + extra_tlds)
        self.tlds_incl_private_trie = Trie.create(self.tlds_incl_private)
        self.tlds_excl_private_trie = Trie.create(self.tlds_excl_private)

    def tlds(self, include_psl_private_domains: bool | None = None) -> frozenset[str]:
        """Get the currently filtered list of suffixes."""
        if include_psl_private_domains is None:
            include_psl_private_domains = self.include_psl_private_domains

        return (
            self.tlds_incl_private
            if include_psl_private_domains
            else self.tlds_excl_private
        )

    def suffix_index(
        self, spl: list[str], include_psl_private_domains: bool | None = None
    ) -> int:
        """Return the index of the first suffix label.

        Returns len(spl) if no suffix is found.
        """
        if include_psl_private_domains is None:
            include_psl_private_domains = self.include_psl_private_domains

        node = (
            self.tlds_incl_private_trie
            if include_psl_private_domains
            else self.tlds_excl_private_trie
        )
        i = len(spl)
        j = i
        for label in reversed(spl):
            decoded_label = _decode_punycode(label)
            if decoded_label in node.matches:
                j -= 1
                if node.matches[decoded_label].end:
                    i = j
                node = node.matches[decoded_label]
                continue

            is_wildcard = "*" in node.matches
            if is_wildcard:
                is_wildcard_exception = "!" + decoded_label in node.matches
                if is_wildcard_exception:
                    return j
                return j - 1

            break

        return i


def _decode_punycode(label: str) -> str:
    lowered = label.lower()
    looks_like_puny = lowered.startswith("xn--")
    if looks_like_puny:
        try:
            return idna.decode(lowered)
        except (UnicodeError, IndexError):
            pass
    return lowered
