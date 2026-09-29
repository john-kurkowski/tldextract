"""tldextract helpers for testing and fetching remote resources."""

from __future__ import annotations

import logging
import pkgutil
import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal, TypedDict, cast

import requests
from requests_file import FileAdapter

from .cache import DiskCache

LOG = logging.getLogger("tldextract")

PUBLIC_SUFFIX_RE = re.compile(r"^(?P<suffix>[.*!]*\w[\S]*)", re.UNICODE | re.MULTILINE)
PUBLIC_PRIVATE_SUFFIX_SEPARATOR = "// ===BEGIN PRIVATE DOMAINS==="
PUBLIC_SUFFIX_SNAPSHOT_PATH = "pkg://tldextract/.tld_set_snapshot"
VERSION_RE = re.compile(r"^// VERSION:\s*(?P<value>.+?)\s*$", re.MULTILINE)
COMMIT_RE = re.compile(r"^// COMMIT:\s*(?P<value>.+?)\s*$", re.MULTILINE)
PkgSnapshotPath = Literal["pkg://tldextract/.tld_set_snapshot"]


@dataclass(frozen=True)
class PslMetadata:
    """Official metadata declared by a Public Suffix List file."""

    version: str
    commit: str | None = None


@dataclass(frozen=True)
class SuffixListInfo:
    """Metadata about the active suffix list loaded by a `TLDExtract` instance."""

    loaded_from: str
    """Source of the active loaded suffix list.

    The packaged snapshot uses the sentinel value
    ``pkg://tldextract/.tld_set_snapshot``.
    """

    psl_metadata: PslMetadata | None = None


@dataclass(frozen=True)
class _LoadedSuffixList:
    """Suffix list payload and metadata returned by the loader."""

    public_suffixes: list[str]
    private_suffixes: list[str]
    suffix_list_info: SuffixListInfo


@dataclass(frozen=True)
class _FetchedSuffixList:
    """Fetched suffix-list text together with the source URL that supplied it."""

    url: str
    text: str


class _SuffixListData(TypedDict):
    """JSON-serializable suffix list data and its metadata."""

    loaded_from: str
    public_suffixes: list[str]
    private_suffixes: list[str]
    psl_metadata: _PslMetadataData | None


class _PslMetadataData(TypedDict):
    """JSON-serializable official PSL metadata."""

    version: str
    commit: str | None


class SuffixListNotFound(LookupError):  # noqa: N818
    """A recoverable error while looking up a suffix list.

    Recoverable because you can specify backups, or use this library's bundled
    snapshot.
    """


def find_first_response(
    cache: DiskCache,
    urls: Sequence[str],
    cache_fetch_timeout: float | int | None = None,
    session: requests.Session | None = None,
) -> _FetchedSuffixList:
    """Return the first successfully fetched URL and its decoded text."""
    session_created = False
    if session is None:
        session = requests.Session()
        session.mount("file://", FileAdapter())
        session_created = True

    try:
        for url in urls:
            try:
                return _FetchedSuffixList(
                    url=url,
                    text=cache.cached_fetch_url(
                        session=session, url=url, timeout=cache_fetch_timeout
                    ),
                )
            except requests.exceptions.RequestException:
                LOG.warning(
                    "Exception reading Public Suffix List url %s", url, exc_info=True
                )
    finally:
        # Ensure the session is always closed if it's constructed in the method
        if session_created:
            session.close()

    raise SuffixListNotFound(
        "No remote Public Suffix List found. Consider using a mirror, or avoid this"
        " fetch by constructing your TLDExtract with `suffix_list_urls=()`."
    )


def extract_tlds_from_suffix_list(suffix_list_text: str) -> tuple[list[str], list[str]]:
    """Parse the raw suffix list text for its different designations of suffixes."""
    public_text, _, private_text = suffix_list_text.partition(
        PUBLIC_PRIVATE_SUFFIX_SEPARATOR
    )

    public_tlds = [m.group("suffix") for m in PUBLIC_SUFFIX_RE.finditer(public_text)]
    private_tlds = [m.group("suffix") for m in PUBLIC_SUFFIX_RE.finditer(private_text)]
    return public_tlds, private_tlds


def get_suffix_lists(
    cache: DiskCache,
    urls: Sequence[str],
    cache_fetch_timeout: float | int | None,
    fallback_to_snapshot: bool,
    session: requests.Session | None = None,
) -> _LoadedSuffixList:
    """Fetch, parse, and cache the suffix lists."""
    result = cache.run_and_cache(
        func=_get_suffix_lists,
        namespace="publicsuffix.org-tlds",
        kwargs={
            "cache": cache,
            "urls": urls,
            "cache_fetch_timeout": cache_fetch_timeout,
            "fallback_to_snapshot": fallback_to_snapshot,
            "session": session,
        },
        hashed_argnames=["urls", "fallback_to_snapshot"],
    )

    if _is_legacy_suffix_list_cache(result):
        data = _get_suffix_lists(
            cache=cache,
            urls=urls,
            cache_fetch_timeout=cache_fetch_timeout,
            fallback_to_snapshot=fallback_to_snapshot,
            session=session,
        )
        cache.set(
            namespace="publicsuffix.org-tlds",
            key={"urls": urls, "fallback_to_snapshot": fallback_to_snapshot},
            value=data,
        )
        return _cached_suffix_list_to_loaded_suffix_list(data)

    return _cached_suffix_list_to_loaded_suffix_list(result)


def _get_suffix_lists(
    cache: DiskCache,
    urls: Sequence[str],
    cache_fetch_timeout: float | int | None,
    fallback_to_snapshot: bool,
    session: requests.Session | None = None,
) -> _SuffixListData:
    """Fetch, parse, and cache the suffix lists."""
    try:
        fetched_suffix_list = find_first_response(
            cache, urls, cache_fetch_timeout=cache_fetch_timeout, session=session
        )
        loaded_from = fetched_suffix_list.url
        text = fetched_suffix_list.text
    except SuffixListNotFound as exc:
        if fallback_to_snapshot:
            maybe_pkg_data = pkgutil.get_data("tldextract", ".tld_set_snapshot")
            # package maintainers guarantee file is included
            pkg_data = cast(bytes, maybe_pkg_data)
            text = pkg_data.decode("utf-8")
            loaded_from = PUBLIC_SUFFIX_SNAPSHOT_PATH
        else:
            raise exc

    public_tlds, private_tlds = extract_tlds_from_suffix_list(text)
    version = _extract_header_value(VERSION_RE, text)
    commit = _extract_header_value(COMMIT_RE, text)
    return {
        "loaded_from": loaded_from,
        "public_suffixes": public_tlds,
        "private_suffixes": private_tlds,
        "psl_metadata": (
            {"version": version, "commit": commit} if version is not None else None
        ),
    }


def _extract_header_value(pattern: re.Pattern[str], text: str) -> str | None:
    """Return the first matching PSL header value from raw suffix-list text."""
    match = pattern.search(text)
    if match is None:
        return None
    return match.group("value")


def _is_legacy_suffix_list_cache(result: object) -> bool:
    """Detect cache entries written before suffix-list metadata was stored."""
    return (
        isinstance(result, list)
        and len(result) == 2
        and all(isinstance(item, list) for item in result)
    )


def _cached_suffix_list_to_loaded_suffix_list(
    cached_suffix_list: _SuffixListData,
) -> _LoadedSuffixList:
    """Convert the JSON cache payload into the loader's richer return type."""
    psl_metadata = cached_suffix_list.get("psl_metadata")

    return _LoadedSuffixList(
        public_suffixes=cached_suffix_list["public_suffixes"],
        private_suffixes=cached_suffix_list["private_suffixes"],
        suffix_list_info=SuffixListInfo(
            loaded_from=cached_suffix_list["loaded_from"],
            psl_metadata=(
                PslMetadata(
                    version=psl_metadata["version"],
                    commit=psl_metadata["commit"],
                )
                if psl_metadata is not None
                else None
            ),
        ),
    )
