"""Tests for the TLDEXTRACT_PUBLIC_SUFFIX_LIST_URLS environment variable."""

import importlib
from pathlib import Path

import pytest

import tldextract.tldextract
from tldextract.tldextract import (
    PUBLIC_SUFFIX_LIST_URLS,
    _suffix_list_urls_from_env,
)

ENV_VAR = "TLDEXTRACT_PUBLIC_SUFFIX_LIST_URLS"


def test_unset_returns_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """When the variable is unset, the given default is returned unchanged."""
    monkeypatch.delenv(ENV_VAR, raising=False)

    assert _suffix_list_urls_from_env() == PUBLIC_SUFFIX_LIST_URLS


def test_newline_delimited_urls(monkeypatch: pytest.MonkeyPatch) -> None:
    """Multiple URLs are split on newlines, and blank lines are ignored."""
    monkeypatch.setenv(
        ENV_VAR,
        "\nhttps://example.com/one.dat\n\n  https://example.com/two.dat  \n",
    )

    assert _suffix_list_urls_from_env() == [
        "https://example.com/one.dat",
        "https://example.com/two.dat",
    ]


def test_empty_string_disables_http(monkeypatch: pytest.MonkeyPatch) -> None:
    """The empty string yields no URLs, which disables HTTP requests."""
    monkeypatch.setenv(ENV_VAR, "")

    assert _suffix_list_urls_from_env() == []


def test_local_file_converted_to_file_uri(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Entries naming an existing local file become file:// URLs, like the CLI."""
    local_file = tmp_path / "list.dat"
    local_file.touch()
    monkeypatch.setenv(ENV_VAR, f"{local_file}\nhttps://example.com/remote.dat")

    assert _suffix_list_urls_from_env() == [
        local_file.as_uri(),
        "https://example.com/remote.dat",
    ]


def test_default_argument_honored(monkeypatch: pytest.MonkeyPatch) -> None:
    """A caller-supplied default is returned when the variable is unset."""
    monkeypatch.delenv(ENV_VAR, raising=False)

    assert _suffix_list_urls_from_env(["https://caller/default.dat"]) == [
        "https://caller/default.dat"
    ]


def test_constructor_default_reads_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """A freshly imported TLDExtract picks up the variable as its default."""
    monkeypatch.setenv(ENV_VAR, "https://example.com/from-env.dat")
    module = importlib.reload(tldextract.tldextract)
    try:
        extract = module.TLDExtract(cache_dir=None)
        assert extract.suffix_list_urls == ("https://example.com/from-env.dat",)
    finally:
        monkeypatch.delenv(ENV_VAR, raising=False)
        importlib.reload(tldextract.tldextract)
