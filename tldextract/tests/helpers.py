'''tldextract test helpers.'''

from subprocess import CalledProcessError, PIPE, Popen
import tempfile


def check_output(*popenargs, **kwargs):
    '''Copied from Python 2.7.'''
    if 'stdout' in kwargs:
        raise ValueError('stdout argument not allowed, it will be overridden.')
    process = Popen(stdout=PIPE, *popenargs, **kwargs)
    output, _ = process.communicate()
    retcode = process.poll()
    if retcode:
        cmd = kwargs.get("args")
        if cmd is None:
            cmd = popenargs[0]
        raise CalledProcessError(retcode, cmd, output=output)
    return output


def temporary_file():
    """ Make a writable temporary file and return its absolute path.
    """
    return tempfile.mkstemp()[1]
