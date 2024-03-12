"""Test the library maintainer release script."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any
from unittest import mock

import pytest
from syrupy.assertion import SnapshotAssertion

from scripts import release


@pytest.fixture
def listdir() -> Iterator[mock.Mock]:
    """Stub listing directory."""
    with mock.patch("os.listdir") as patched:
        yield patched


@pytest.fixture
def requests() -> Iterator[mock.Mock]:
    """Stub network requests."""
    with mock.patch("requests.post") as patched:
        yield patched


@pytest.fixture
def subprocess() -> Iterator[mock.Mock]:
    """Stub running external commands."""
    with mock.patch("subprocess.run") as patched:
        patched.return_value.stdout = ""
        yield patched


def test_happy_path(
    capsys: pytest.CaptureFixture[str],
    listdir: mock.Mock,
    monkeypatch: pytest.MonkeyPatch,
    requests: mock.Mock,
    snapshot: SnapshotAssertion,
    subprocess: mock.Mock,
) -> None:
    """Test the release script happy path.

    Simulate user input for a typical, existing release.

    This one test case covers most lines of the release script, without
    actually making network requests or running subprocesses. For an
    infrequently used script, this coverage is useful without being too brittle
    to change.
    """
    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")

    input_values = iter(["y", "5.0.1", "y"])

    def cycle_input_values(prompt: str) -> str:
        return next(input_values)

    monkeypatch.setattr("builtins.input", cycle_input_values)

    def mock_post(*args: Any, **kwargs: Any) -> mock.Mock:
        return mock.Mock(
            json=mock.Mock(
                return_value={
                    "body": "Body start **Full Changelog**: fake-body",
                    "html_url": "https://github.com/path/to/release",
                }
            ),
        )

    requests.side_effect = mock_post

    release.main()

    out, err = capsys.readouterr()

    assert listdir.call_args_list == snapshot
    assert requests.call_args_list == snapshot
    assert subprocess.call_args_list == snapshot
    assert out == snapshot
    assert err == snapshot
