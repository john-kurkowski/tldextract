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
uv run ruff format .
uv run tox --parallel -e py310,codestyle,lint,typecheck
```

Formatting runs first because it mutates files. The remaining checks are safe to
run concurrently. When debugging a failure, rerun its individual environment
serially for clearer output.

Run broader validation when the scope warrants it:

```zsh
uv run tox --parallel  # Run everything: pytest on all Pythons + codestyle + lint + typecheck
```

The `py*` and `pypy*` environments forward to `pytest`; `codestyle`, `lint`, and
`typecheck` do not.
