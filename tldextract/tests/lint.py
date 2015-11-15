'''Lint tests.'''

import itertools
import os
import pylint.epylint
import re
import sys
import unittest

from .helpers import check_output


class PylintTestMeta(type):
    '''Dynamically generates a test case for every Pylint error.'''

    def __new__(mcs, name, bases, di):
        '''Runs all Python files in this project through Pylint. For each lint
        error, adds a test case method to `di`.'''
        project_root = check_output(('git', 'rev-parse', '--show-toplevel')).strip()

        ls_files_cmd = ('git', '--git-dir', os.path.join(project_root, '.git'), 'ls-files')
        ls_files = check_output(ls_files_cmd).splitlines()
        py_files = (os.path.join(project_root, f) for f in ls_files if f.endswith('.py'))

        pylint_errors = itertools.chain.from_iterable(
            mcs.pylint_errors(project_root, py_file) for py_file in py_files
        )
        for pylint_error in pylint_errors:
            test_name = 'test {} {}'.format(
                pylint_error.group('location'),
                pylint_error.group('category')
            )
            test_msg = pylint_error.group('message')
            test_method = mcs.generate_lint_fail_method(test_msg)
            di[test_name] = test_method

        return type.__new__(mcs, name, bases, di)

    @classmethod
    def generate_lint_fail_method(mcs, test_msg):
        def lint_fail(self):
            self.assertTrue(False, test_msg)
        return lint_fail

    @classmethod
    def pylint_errors(mcs, project_root, py_file):
        '''Yield Pylint errors as instances of re.MatchObject.'''
        # Match example:
        # tldextract/tldextract.py:337: convention (C0111, missing-docstring, _PublicSuffixListTLDExtractor) Missing class docstring # pylint: disable=line-too-long
        pylint_line_re = re.compile(r'''
            \s*{}{}                     # Ignore absolute path outside project root
            (?P<location>\S+\d+)        # File and lineno the error occurs
            :\s*
            (?P<category>\S+)           # e.g. convention, info, fatal
            \s*
            (?P<code>\(.+?\))           # Pylint code tuple
            \s*
            (?P<message>.+)             # Exact error message
        '''.format(project_root, os.path.sep), re.VERBOSE)

        exclude_categories = set(('info',))

        pylintrc = os.path.join(project_root, 'pylintrc')
        pylint_opts = '{} --rcfile={}'.format(py_file, pylintrc)
        stdout, _ = pylint.epylint.py_run(pylint_opts, return_std=True)
        for line in stdout.readlines():
            match = pylint_line_re.match(line)
            if match and match.group('category') not in exclude_categories:
                yield match


class PylintTest(unittest.TestCase):

    __metaclass__ = PylintTestMeta


def run_tests(stream=sys.stderr):
    suite = unittest.TestSuite([
        unittest.TestLoader().loadTestsFromTestCase(PylintTest)
    ])
    unittest.TextTestRunner(stream).run(suite)


if __name__ == '__main__':
    run_tests()
