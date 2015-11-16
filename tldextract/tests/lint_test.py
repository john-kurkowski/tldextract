'''Lint tests.'''

import os
import pylint.epylint
import re
import sys

from .helpers import check_output

if sys.version_info >= (3, 0):
    unicode = str # pylint: disable=invalid-name,redefined-builtin


SKIPPED_LINT = ()
NO_LINT_ERRORS = ('',)


def test_lint_error(lint_error):
    assert not lint_error


def pytest_generate_tests(metafunc):
    '''Runs all Python files in this project through Pylint. For each lint
    error, adds corresponding failing test case.'''
    is_pylint_compatible = (2, 7) <= sys.version_info < (3, 5)
    if not is_pylint_compatible:
        metafunc.parametrize('lint_error', SKIPPED_LINT)
        return

    project_root_cmd = ('git', 'rev-parse', '--show-toplevel')
    project_root = unicode(check_output(project_root_cmd), 'utf-8').strip()

    ls_files_cmd = ('git', '--git-dir', os.path.join(project_root, '.git'), 'ls-files')
    ls_files = (unicode(f, 'utf-8') for f in check_output(ls_files_cmd).splitlines())
    py_files = (os.path.join(project_root, f) for f in ls_files if f.endswith('.py'))

    errors = [
        error
        for py_file in py_files
        for error in pylint_errors(project_root, py_file)
    ]

    metafunc.parametrize('lint_error', errors or NO_LINT_ERRORS)


def pylint_errors(project_root, py_file):
    '''Yield Pylint errors from the given Python file.'''
    # Match example:
    # tldextract/tldextract.py:337: convention (C0111, missing-docstring, _PublicSuffixListTLDExtractor) Missing class docstring # pylint: disable=line-too-long
    pylint_line_re = re.compile(r'''
        \s*{}{}                     # Ignore absolute path outside project root
        (?P<relative_line>
        (?P<location>\S+\d+)        # File and lineno the error occurs
        :\s*
        (?P<category>\S+)           # e.g. convention, info, fatal
        \s*
        (?P<code>\(.+?\))           # Pylint code tuple
        \s*
        (?P<message>.+)             # Exact error message
        )
    '''.format(project_root, os.path.sep), re.VERBOSE)

    exclude_categories = set(('info',))

    pylintrc = os.path.join(project_root, 'pylintrc')
    pylint_opts = '{} --rcfile={}'.format(py_file, pylintrc)
    stdout, stderr = pylint.epylint.py_run(pylint_opts, return_std=True)

    stderr_str = stderr.read()
    looks_like_pylint_exit_error = len(stderr_str) > 200
    if looks_like_pylint_exit_error:
        raise Exception('`pylint {}` exited with error\n{}'.format(pylint_opts, stderr_str))

    for line in stdout.readlines():
        match = pylint_line_re.match(line)
        if match and match.group('category') not in exclude_categories:
            yield match.group('relative_line')
