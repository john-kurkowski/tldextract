"""Test the library maintainer release script."""

from __future__ import annotations

import dataclasses
import sys
from collections.abc import Iterator
from typing import Any
from unittest import mock

import pytest
from syrupy.assertion import SnapshotAssertion

from scripts import release


@dataclasses.dataclass
class Mocks:
    """Collection of all mocked objects used in the release script."""

    input: mock.Mock
    listdir: mock.Mock
    requests: mock.Mock
    subprocess: mock.Mock

    @property
    def mock_calls(self) -> dict[str, Any]:
        """A dict of _all_ calls to this class's mock objects."""
        return {
            k.name: getattr(self, k.name).mock_calls for k in dataclasses.fields(self)
        }


@pytest.fixture
def mocks() -> Iterator[Mocks]:
    """Stub network and subprocesses."""
    with (
        mock.patch("builtins.input") as mock_input,
        mock.patch("os.listdir") as mock_listdir,
        mock.patch("requests.post") as mock_requests,
        mock.patch("subprocess.run") as mock_subprocess,
    ):
        yield Mocks(
            input=mock_input,
            listdir=mock_listdir,
            requests=mock_requests,
            subprocess=mock_subprocess,
        )


@pytest.mark.skipif(
    sys.platform == "win32", reason="Snapshot paths are different on Windows"
)
def test_happy_path(
    capsys: pytest.CaptureFixture[str],
    mocks: Mocks,
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

    mocks.input.side_effect = ["y", "5.0.1", "y"]

    mocks.listdir.return_value = ["archive1", "archive2", "archive3"]

    def mock_post(*args: Any, **kwargs: Any) -> mock.Mock:
        """Return _one_ response JSON that happens to match expectations for multiple requests."""
        return mock.Mock(
            json=mock.Mock(
                return_value={
                    "body": "## What's Changed\nGitHub changelog here\n\n## New Contributors\n* @jdoe contributed\n\n**Full Changelog**: fake-body",
                    "html_url": "https://github.com/path/to/release",
                }
            ),
        )

    mocks.requests.side_effect = mock_post

    mocks.subprocess.return_value.stdout = ""

    release.main()

    out, err = capsys.readouterr()

    assert mocks.mock_calls == snapshot
    assert out == snapshot
    assert err == snapshot
