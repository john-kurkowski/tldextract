import os
import sys

if __name__ == "__main__":
    cwd = os.path.dirname(__file__)
    sys.path.append(os.path.abspath(os.path.join(cwd, os.pardir)))
    for mod in ('tldextract', 'web'):
        mod = __import__(mod)
        loc = os.path.dirname(mod.__file__)
        symlink = os.path.join(cwd, mod.__name__)
        os.symlink(loc, symlink)
    sys.exit(0)

