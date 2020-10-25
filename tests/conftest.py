"""py.test standard config file."""

import logging

import pytest
import tldextract.cache


@pytest.fixture(autouse=True)
def reset_log_level():
    """Automatically reset log level verbosity between tests. Generally want
    test output the Unix way: silence is golden."""
    tldextract.cache._DID_LOG_UNABLE_TO_CACHE = (  # pylint: disable=protected-access
        False
    )
    logging.getLogger().setLevel(logging.WARN)
