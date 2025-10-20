"""py.test standard config file."""

import logging

import pytest

import tldextract.cache


@pytest.fixture(autouse=True)
def reset_log_level() -> None:
    """Automatically reset log level verbosity between tests.

    Generally want test output the Unix way: silence is golden.
    """
    tldextract.cache._DID_LOG_UNABLE_TO_CACHE = False
    logging.getLogger().setLevel(logging.WARN)
