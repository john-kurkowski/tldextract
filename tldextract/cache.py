"""Helpers """
import errno
import json
import logging
import os
import os.path
from hashlib import md5

from filelock import FileLock

try:
    unicode
except NameError:
    unicode = str  # pylint: disable=invalid-name,redefined-builtin

try:
    FileNotFoundError
except NameError:
    class FileNotFoundError(Exception):
        pass

LOG = logging.getLogger(__name__)


class DiskCache(object):
    """Disk _cache that only works for jsonable values"""

    def __init__(self, cache_dir, lock_timeout=20):
        self.enabled = bool(cache_dir)
        self.cache_dir = os.path.expanduser(str(cache_dir) or '')
        self.lock_timeout = lock_timeout
        # using a unique extension provides some safety that an incorrectly set cache_dir
        # combined with a call to `.clear()` wont wipe someones hard drive
        self.file_ext = ".tldextract.json"

    def get(self, namespace, key):
        """Retrieve a value from the disk cache"""
        if not self.enabled:
            raise KeyError("Cache is disabled")
        cache_filepath = self._key_to_cachefile_path(namespace, key)

        if not os.path.isfile(cache_filepath):
            raise KeyError("namespace: " + namespace + " key: " + repr(key))
        try:
            with open(cache_filepath) as cache_file:
                return json.load(cache_file)
        except (IOError, ValueError) as exc:
            LOG.error(
                "error reading TLD cache file %s: %s",
                cache_filepath,
                exc
            )
            raise KeyError("namespace: " + namespace + " key: " + repr(key))

    def set(self, namespace, key, value):
        """Set a value in the disk cache"""
        if not self.enabled:
            return False
        cache_filepath = self._key_to_cachefile_path(namespace, key)

        try:
            with open(cache_filepath, 'w') as cache_file:
                json.dump(value, cache_file)
        except IOError as ioe:
            LOG.warning(
                (
                    "unable to cache %s.%s in %s. This could refresh the "
                    "Public Suffix List over HTTP every app startup. "
                    "Construct your `TLDExtract` with a writable `cache_dir` or "
                    "set `cache_dir=False` to silence this warning. %s"
                ),
                namespace,
                key,
                cache_filepath,
                ioe,
            )
        return None

    def clear(self):
        """Clear the disk cache"""
        for root, _, files in os.walk(self.cache_dir):
            for filename in files:
                if filename.endswith(self.file_ext) or filename.endswith(self.file_ext + ".lock"):
                    try:
                        os.unlink(os.path.join(root, filename))
                    except FileNotFoundError:
                        pass
                    except OSError as exc:
                        # errno.ENOENT == "No such file or directory"
                        # https://docs.python.org/2/library/errno.html#errno.ENOENT
                        if exc.errno != errno.ENOENT:
                            raise

    def _key_to_cachefile_path(self, namespace, key):
        namespace_path = os.path.join(self.cache_dir, namespace)
        hashed_key = _make_cache_key(key)

        cache_path = os.path.join(namespace_path, hashed_key + self.file_ext)

        _make_dir(cache_path)
        return cache_path

    def run_and_cache(self, func, namespace, kwargs, hashed_argnames):
        """Get a url but cache the response"""
        if not self.enabled:
            return func(**kwargs)

        key_args = {k: v for k, v in kwargs.items() if k in hashed_argnames}
        cache_filepath = self._key_to_cachefile_path(namespace, key_args)
        lock_path = cache_filepath + '.lock'
        # print(lock_path)
        with FileLock(lock_path, timeout=self.lock_timeout):
            try:
                result = self.get(namespace=namespace, key=key_args)
            except KeyError:
                result = func(**kwargs)
                self.set(namespace="urls", key=key_args, value=result)

            return result

    def cached_fetch_url(self, session, url, timeout):
        """Get a url but cache the response"""
        return self.run_and_cache(
            func=_fetch_url,
            namespace="urls",
            kwargs={
                "session": session,
                "url": url,
                "timeout": timeout
            },
            hashed_argnames=["url"]
        )


def _fetch_url(session, url, timeout):

    response = session.get(url, timeout=timeout)
    response.raise_for_status()
    text = response.text

    if not isinstance(text, unicode):
        text = unicode(text, 'utf-8')

    return text


def _make_cache_key(inputs):
    key = repr(inputs)
    try:
        key = md5(key).hexdigest()
    except TypeError:
        key = md5(key.encode('utf8')).hexdigest()
    return key


def _make_dir(filename):
    """Make a directory if it doesn't already exist"""
    if not os.path.exists(os.path.dirname(filename)):
        try:
            os.makedirs(os.path.dirname(filename))
        except OSError as exc:  # Guard against race condition
            if exc.errno != errno.EEXIST:
                raise
