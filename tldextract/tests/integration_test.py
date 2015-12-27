'''tldextract integration tests.'''

import logging
import os
import pytest
import traceback

import tldextract


def test_log_snapshot_diff(mocker):
    mocker.patch.object(logging.getLogger(), 'level', logging.DEBUG)
    debug_mock = mocker.patch.object(logging.getLogger('tldextract'), 'debug')

    extractor = tldextract.TLDExtract()
    try:
        os.remove(extractor.cache_file)
    except (IOError, OSError):
        logging.warning(traceback.format_exc())

    extractor('ignore.com')

    assert debug_mock.call_count == 1
    log_str = debug_mock.call_args[0][0]
    assert log_str.startswith('computed TLD diff')


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
