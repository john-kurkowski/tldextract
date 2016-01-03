'tldextract helpers for testing and fetching remote resources.'


import logging
import re
import socket

# pylint: disable=import-error,invalid-name,no-name-in-module,redefined-builtin
try:  # pragma: no cover
    # Python 2
    from urllib2 import urlopen
    from urlparse import scheme_chars
except ImportError:  # pragma: no cover
    # Python 3
    from urllib.request import urlopen
    from urllib.parse import scheme_chars
    unicode = str
# pylint: enable=import-error,invalid-name,no-name-in-module,redefined-builtin


IP_RE = re.compile(r'^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$') # pylint: disable=line-too-long
SCHEME_RE = re.compile(r'^([' + scheme_chars + ']+:)?//')

LOG = logging.getLogger('tldextract')


def find_first_response(urls):
    """ Decode the first successfully fetched URL, from UTF-8 encoding to
    Python unicode.
    """
    text = ''

    for url in urls:
        try:
            conn = urlopen(url)
            text = conn.read()
        except IOError as ioe:
            LOG.error('Exception reading Public Suffix List url ' + url + ' - ' + str(ioe) + '.')
        else:
            return _decode_utf8(text)

    LOG.error(
        'No Public Suffix List found. Consider using a mirror or constructing '
        'your TLDExtract with `suffix_list_url=None`.'
    )
    return unicode('')


def _decode_utf8(text):
    """ Decode from utf8 to Python unicode string.

    The suffix list, wherever its origin, should be UTF-8 encoded.
    """
    return unicode(text, 'utf-8')


def looks_like_ip(maybe_ip):
    """Does the given str look like an IP address?"""
    if not maybe_ip[0].isdigit():
        return False

    try:
        socket.inet_aton(maybe_ip)
        return True
    except (AttributeError, UnicodeError):
        if IP_RE.match(maybe_ip):
            return True
    except socket.error:
        return False
