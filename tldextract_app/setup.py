'''tldextract GAE app setup.py'''

import os
import sys


def main():
    # Must include deps in this folder for GAE. It doesn't use a e.g.
    # requirements.txt.
    app_folder = os.path.dirname(__file__)
    sys.path.append(os.path.abspath(os.path.join(app_folder, os.pardir)))
    deps = ('tldextract', 'web')
    for modname in deps:
        symlink = os.path.join(app_folder, modname)
        try:
            os.remove(symlink)
        except (OSError, IOError):
            pass

        mod = __import__(modname)
        loc = os.path.dirname(mod.__file__)
        os.symlink(loc, symlink)


if __name__ == "__main__":
    main()
