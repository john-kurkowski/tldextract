"""Helpers """
import errno
import json
import os.path
from hashlib import md5

from six import wraps


def cache_to_jsonfile(path, ignore_kwargs=()):
    """Decorator to cache a function to a json file"""

    def decorator(func):
        """Actual decorator"""

        @wraps(func)
        def return_cache(*args, **kwargs):
            """wrapping function"""
            assert not args
            key_args = {k: v for k, v in kwargs.items() if k not in ignore_kwargs}
            key = _cache_make_key(*args, **key_args)

            cache_path = path + '/' + key + '.json'
            cache_path = cache_path.replace('//', '/')

            if not os.path.isfile(cache_path):
                result = func(*args, **kwargs)
                make_dir(cache_path)
                with open(cache_path, 'w') as cache_file:
                    json.dump(result, cache_file)

            with open(cache_path) as cache_file:
                return json.load(cache_file)

        return return_cache

    return decorator


def _cache_make_key(*args, **kwargs):
    """Make a key out of the arguments"""
    key = repr((args, kwargs))
    try:
        key = md5(key).hexdigest()
    except TypeError:
        key = md5(key.encode('utf8')).hexdigest()
    return key


def make_dir(filename):
    """Make a directory if it doesn't already exist"""
    if not os.path.exists(os.path.dirname(filename)):
        try:
            os.makedirs(os.path.dirname(filename))
        except OSError as exc:  # Guard against race condition
            if exc.errno != errno.EEXIST:
                raise
