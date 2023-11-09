"""Test ability to run in parallel with shared cache."""

from __future__ import annotations

import os
from multiprocessing import Pool
from pathlib import Path

import pytest
import responses

from tldextract import TLDExtract
from tldextract.tldextract import PUBLIC_SUFFIX_LIST_URLS


def test_multiprocessing_makes_one_request(tmp_path: Path) -> None:
    """Ensure there aren't duplicate download requests."""
    process_count = 3
    with Pool(processes=process_count) as pool:
        http_request_counts = pool.map(_run_extractor, [tmp_path] * process_count)
    assert sum(http_request_counts) == 1


def _run_extractor(cache_dir: Path) -> int:
    """Run the extractor."""
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        rsps.add(responses.GET, PUBLIC_SUFFIX_LIST_URLS[0], status=208, body="uk.co")
        extract = TLDExtract(cache_dir=str(cache_dir))

        extract("bar.uk.com", include_psl_private_domains=True)
        num_calls = len(rsps.calls)
    return num_calls


@responses.activate
def test_cache_cleared_by_other_process(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Simulate a file being deleted after we check for existence but before we try to delete it."""
    responses.add(responses.GET, PUBLIC_SUFFIX_LIST_URLS[0], status=208, body="uk.com")

    cache_dir = str(tmp_path)
    extract = TLDExtract(cache_dir=cache_dir)
    extract("google.com")
    orig_unlink = os.unlink

    def evil_unlink(filename: str | Path) -> None:
        """Simulate someone deletes the file right before we try to."""
        if (isinstance(filename, str) and filename.startswith(cache_dir)) or (
            isinstance(filename, Path) and filename.is_relative_to(cache_dir)
        ):
            orig_unlink(filename)
        orig_unlink(filename)

    monkeypatch.setattr(os, "unlink", evil_unlink)

    extract.update(fetch_now=True)
