import os
import sys

if __name__ == "__main__":
    # Must include deps in this folder for GAE. It doesn't use a e.g.
    # requirements.txt.
    cwd = os.path.dirname(__file__)
    sys.path.append(os.path.abspath(os.path.join(cwd, os.pardir)))
    deps = ('tldextract', 'web')
    for modname in deps:
        symlink = os.path.join(cwd, modname)
        try:
            os.remove(symlink)
        except (OSError, IOError) as e:
            pass

        mod = __import__(modname)
        loc = os.path.dirname(mod.__file__)
        os.symlink(loc, symlink)
