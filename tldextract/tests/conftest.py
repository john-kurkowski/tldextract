'''py.test standard config file.'''

import logging
import pytest


@pytest.fixture(autouse=True)
def reset_log_level():
    logging.getLogger().setLevel(logging.WARN)
