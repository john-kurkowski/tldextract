"""py.test standard config file."""

import logging

import pytest


@pytest.fixture(autouse=True)
def reset_log_level():
    """Automatically reset log level verbosity between tests. Generally want
    test output the Unix way: silence is golden."""
    logging.getLogger().setLevel(logging.WARN)
