'''tldextract integration tests.'''

import logging
import os
import pytest
import traceback

import tldextract


def test_log_snapshot_diff():
    logging.getLogger().setLevel(logging.DEBUG)

    extractor = tldextract.TLDExtract()
    try:
        os.remove(extractor.cache_file)
    except (IOError, OSError):
        logging.warning(traceback.format_exc())

    # TODO: if .tld_set_snapshot is up to date, this won't trigger a diff
    extractor('ignore.com')


def test_bad_kwargs():
    with pytest.raises(ValueError):
        tldextract.TLDExtract(
            cache_file=False, suffix_list_url=False, fallback_to_snapshot=False
        )


def test_fetch_and_suffix_list_conflict():
    """ Make sure we support both fetch and suffix_list_url kwargs for this version.

    GitHub issue #41.
    """
    extractor = tldextract.TLDExtract(suffix_list_url='foo', fetch=False)
    assert not extractor.suffix_list_urls
