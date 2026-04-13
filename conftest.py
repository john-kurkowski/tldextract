"""Project-wide pytest configuration.

This lives at the repo root so pytest can collect root-level docs like
README.md via Sybil. Test-only fixtures still live under tests/conftest.py.
"""

from sybil import Sybil
from sybil.parsers.markdown import PythonCodeBlockParser

pytest_collect_file = Sybil(
    parsers=[PythonCodeBlockParser()],
    patterns=["README.md"],
).pytest()
