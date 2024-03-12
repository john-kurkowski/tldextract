"""Test the library maintainer release script."""

from __future__ import annotations

import sys
from collections.abc import Iterator
from typing import Any
from unittest import mock

import pytest
from syrupy.assertion import SnapshotAssertion

from scripts import release


@pytest.fixture
def mock_input() -> Iterator[mock.Mock]:
    """Stub reading user input."""
    with mock.patch("builtins.input") as patched:
        yield patched


@pytest.fixture
def mock_listdir() -> Iterator[mock.Mock]:
    """Stub listing directory."""
    with mock.patch("os.listdir") as patched:
        yield patched


@pytest.fixture
def mock_requests() -> Iterator[mock.Mock]:
    """Stub network requests."""
    with mock.patch("requests.post") as patched:
        yield patched


@pytest.fixture
def mock_subprocess() -> Iterator[mock.Mock]:
    """Stub running external commands."""
    with mock.patch("subprocess.run") as patched:
        yield patched


@pytest.mark.xfail(
    sys.platform == "win32", reason="Snapshot paths are different on Windows"
)
def test_happy_path(
    capsys: pytest.CaptureFixture[str],
    mock_input: mock.Mock,
    mock_listdir: mock.Mock,
    mock_requests: mock.Mock,
    mock_subprocess: mock.Mock,
    monkeypatch: pytest.MonkeyPatch,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the release script happy path.

    Simulate user input for a typical, existing release.

    This one test case covers most lines of the release script, without
    actually making network requests or running subprocesses. For an
    infrequently used script, this coverage is useful without being too brittle
    to change.
    """
    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")

    mock_input.side_effect = ["y", "5.0.1", "y"]

    def mock_post(*args: Any, **kwargs: Any) -> mock.Mock:
        """Return _one_ response JSON that happens to match expectations for multiple requests."""
        return mock.Mock(
            json=mock.Mock(
                return_value={
                    "body": "Body start **Full Changelog**: fake-body",
                    "html_url": "https://github.com/path/to/release",
                }
            ),
        )

    mock_requests.side_effect = mock_post

    release.main()

    out, err = capsys.readouterr()

    assert mock_input.call_args_list == snapshot
    assert mock_listdir.call_args_list == snapshot
    assert mock_requests.call_args_list == snapshot
    assert mock_subprocess.call_args_list == snapshot
    assert out == snapshot
    assert err == snapshot
