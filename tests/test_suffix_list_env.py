"""Tests for the TLDEXTRACT_PUBLIC_SUFFIX_LIST_URLS environment variable."""

import os
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

import pytest
import pytest_mock

import tldextract

ENV_VAR = "TLDEXTRACT_PUBLIC_SUFFIX_LIST_URLS"


def test_unset_uses_standard_urls(monkeypatch: pytest.MonkeyPatch) -> None:
    """An unset environment variable preserves the standard URL order."""
    monkeypatch.delenv(ENV_VAR, raising=False)

    assert tldextract.TLDExtract(cache_dir=None).suffix_list_urls == (
        "https://publicsuffix.org/list/public_suffix_list.dat",
        "https://raw.githubusercontent.com/publicsuffix/list/master/public_suffix_list.dat",
    )


def test_newline_delimited_urls(monkeypatch: pytest.MonkeyPatch) -> None:
    """New instances split URLs on newlines and ignore blank lines."""
    monkeypatch.setenv(
        ENV_VAR,
        "\nhttps://example.com/one.dat\n\n  https://example.com/two.dat  \n",
    )

    assert tldextract.TLDExtract(cache_dir=None).suffix_list_urls == (
        "https://example.com/one.dat",
        "https://example.com/two.dat",
    )


def test_constructor_reads_current_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Each new instance reads the environment at construction time."""
    monkeypatch.setenv(ENV_VAR, "https://example.com/first.dat")
    first = tldextract.TLDExtract(cache_dir=None)
    monkeypatch.setenv(ENV_VAR, "https://example.com/second.dat")

    assert first.suffix_list_urls == ("https://example.com/first.dat",)
    assert tldextract.TLDExtract(cache_dir=None).suffix_list_urls == (
        "https://example.com/second.dat",
    )


def test_empty_string_uses_snapshot_without_http(
    monkeypatch: pytest.MonkeyPatch, mocker: pytest_mock.MockerFixture
) -> None:
    """An empty value prevents HTTP fetches and permits snapshot fallback."""
    monkeypatch.setenv(ENV_VAR, "")
    http_get = mocker.patch("requests.Session.get")

    extract = tldextract.TLDExtract(cache_dir=None)

    assert extract.suffix_list_urls == ()
    assert extract("example.com").suffix == "com"
    http_get.assert_not_called()


def test_local_file_supplies_suffixes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A local path is converted to a file URL and used as the suffix list."""
    local_file = tmp_path / "list.dat"
    local_file.write_text("custom\n", encoding="utf-8")
    monkeypatch.setenv(ENV_VAR, str(local_file))

    extract = tldextract.TLDExtract(cache_dir=None, fallback_to_snapshot=False)

    assert extract.suffix_list_urls == (local_file.as_uri(),)
    assert extract("example.custom").suffix == "custom"


def test_explicit_urls_take_precedence(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """An explicit suffix list overrides the environment default."""
    local_file = tmp_path / "explicit.dat"
    local_file.write_text("explicit\n", encoding="utf-8")
    monkeypatch.setenv(ENV_VAR, "https://example.com/from-env.dat")

    extract = tldextract.TLDExtract(
        cache_dir=None,
        suffix_list_urls=(local_file.as_uri(),),
        fallback_to_snapshot=False,
    )

    assert extract.suffix_list_urls == (local_file.as_uri(),)
    assert extract("example.explicit").suffix == "explicit"


@pytest.mark.parametrize("suffix_list_urls", [(), []])
def test_explicit_empty_urls_disable_http(
    monkeypatch: pytest.MonkeyPatch,
    mocker: pytest_mock.MockerFixture,
    suffix_list_urls: Sequence[str],
) -> None:
    """Explicit empty sequences override the environment default."""
    monkeypatch.setenv(ENV_VAR, "https://example.com/from-env.dat")
    http_get = mocker.patch("requests.Session.get")

    extract = tldextract.TLDExtract(cache_dir=None, suffix_list_urls=suffix_list_urls)

    assert extract.suffix_list_urls == ()
    assert extract("example.com").suffix == "com"
    http_get.assert_not_called()


def test_explicit_none_keeps_runtime_no_fetch(
    monkeypatch: pytest.MonkeyPatch, mocker: pytest_mock.MockerFixture
) -> None:
    """Explicit None still disables fetching, though it is outside the typed API."""
    monkeypatch.setenv(ENV_VAR, "https://example.com/from-env.dat")
    http_get = mocker.patch("requests.Session.get")

    extract = tldextract.TLDExtract(
        cache_dir=None,
        suffix_list_urls=None,  # type: ignore[arg-type]
    )

    assert extract.suffix_list_urls == ()
    assert extract("example.com").suffix == "com"
    http_get.assert_not_called()


def test_public_extract_reads_env_before_import(tmp_path: Path) -> None:
    """The module-level extractor uses the environment present at import."""
    local_file = tmp_path / "list.dat"
    local_file.write_text("custom\n", encoding="utf-8")
    env = {**os.environ, ENV_VAR: str(local_file)}

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import tldextract; print(tldextract.extract('example.custom').suffix)",
        ],
        check=True,
        capture_output=True,
        env=env,
        text=True,
        timeout=10,
    )

    assert result.stdout == "custom\n"
