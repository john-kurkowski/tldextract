# Repository Guidance

See [README.md](README.md) for contributor setup.

## Tests

While iterating on a change, prefer the smallest test invocation that exercises
the behavior you are working on, such as a specific test file or pytest `-k`
selector:

```zsh
uv run tox -e py310 -- tests/cli_test.py
uv run tox -e py310 -- -k private
```

Before wrapping up any code change, always run the required validation baseline:

```zsh
uv run tox -e py310         # Fastest full pytest run while iterating
uv run tox -e lint          # Lint (ruff check)
uv run tox -e typecheck     # Type-check (mypy)
uv run ruff format .        # Auto-format code
```

Run broader validation when the scope warrants it:

```zsh
uv run tox --parallel  # Run everything: pytest on all Pythons + codestyle + lint + typecheck
```

The `py*` and `pypy*` environments forward to `pytest`; `codestyle`, `lint`, and
`typecheck` do not.
