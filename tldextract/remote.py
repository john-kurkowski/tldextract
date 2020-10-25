'tldextract helpers for testing and fetching remote resources.'

import re
import socket

from urllib.parse import scheme_chars


IP_RE = re.compile(
    r'^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$')  # pylint: disable=line-too-long

SCHEME_RE = re.compile(r'^([' + scheme_chars + ']+:)?//')


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
