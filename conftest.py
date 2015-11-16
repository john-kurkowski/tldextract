'''py.test standard config file.'''

import sys

# pylint: disable=invalid-name

collect_ignore = ('setup.py',)

# pylint: enable=invalid-name

def pytest_cmdline_preparse(args):
    is_pylint_compatible = (2, 7) <= sys.version_info < (3, 5)
    if not is_pylint_compatible:
        args.remove('--pylint')
