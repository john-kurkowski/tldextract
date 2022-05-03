"""tldextract integration tests."""

import sys

import pytest

from tldextract.cli import main


def test_cli_no_input(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tldextract"])
    with pytest.raises(SystemExit) as ex:
        main()

    assert ex.value.code == 1


def test_cli_parses_args(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tldextract", "--some", "nonsense"])
    with pytest.raises(SystemExit) as ex:
        main()

    assert ex.value.code == 2


def test_cli_posargs(capsys, monkeypatch):
    monkeypatch.setattr(
        sys, "argv", ["tldextract", "example.com", "bbc.co.uk", "forums.bbc.co.uk"]
    )

    main()

    stdout, stderr = capsys.readouterr()
    assert not stderr
    assert stdout == " example com\n bbc co.uk\nforums bbc co.uk\n"
