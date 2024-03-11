"""Test the library maintainer release script."""

import pytest

from scripts import release


def test_happy_path() -> None:
    """Test the release script happy path."""
    assert release
    pytest.xfail("Not implemented yet")
