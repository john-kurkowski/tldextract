'''tldextract test helpers.'''

from subprocess import CalledProcessError, PIPE, Popen
import tempfile


def temporary_dir():
    """ Make a writable temporary file and return its absolute path.
    """
    return tempfile.mkdtemp()
