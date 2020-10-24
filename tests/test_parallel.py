"""Test ability to run in parallel with shared cache"""
import os
import os.path
from multiprocessing import Pool

import responses

from tldextract import TLDExtract
from tldextract.tldextract import PUBLIC_SUFFIX_LIST_URLS


def test_multiprocessing_makes_one_request(tmpdir):
    """Ensure there aren't duplicate download requests"""
    process_count = 3
    pool = Pool(processes=process_count)

    http_request_counts = pool.map(_run_extractor, [str(tmpdir)] * process_count)
    assert sum(http_request_counts) == 1


@responses.activate
def _run_extractor(cache_dir):
    """run the extractor"""
    responses.add(
        responses.GET,
        PUBLIC_SUFFIX_LIST_URLS[0],
        status=208,
        body="uk.co"
    )
    extract = TLDExtract(cache_dir=cache_dir)

    extract("bar.uk.com", include_psl_private_domains=True)
    return len(responses.calls)


@responses.activate
def test_cache_cleared_by_other_process(tmpdir, monkeypatch):
    """Simulate a file being deleted after we check for existence but before we try to delete it"""
    responses.add(
        responses.GET,
        PUBLIC_SUFFIX_LIST_URLS[0],
        status=208,
        body="uk.com"
    )

    cache_dir = str(tmpdir)
    extract = TLDExtract(cache_dir=cache_dir)
    extract("google.com")
    orig_unlink = os.unlink

    def evil_unlink(filename):
        """Simulates someone delete the file right before we try to"""
        if filename.startswith(cache_dir):
            orig_unlink(filename)
        orig_unlink(filename)

    monkeypatch.setattr(os, "unlink", evil_unlink)

    extract.update(fetch_now=True)
