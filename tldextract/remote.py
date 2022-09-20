"tldextract helpers for testing and fetching remote resources."

import re
import socket
from urllib.parse import scheme_chars

IP_RE = re.compile(
    # pylint: disable-next=line-too-long
    r"^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$"
)

SCHEME_RE = re.compile(r"^([" + scheme_chars + "]+:)?//")


def lenient_netloc(url: str) -> str:
    """Extract the netloc of a URL-like string, similar to the netloc attribute
    returned by urllib.parse.{urlparse,urlsplit}, but extract more leniently,
    without raising errors."""

    return (
        SCHEME_RE.sub("", url)
        .partition("/")[0]
        .partition("?")[0]
        .partition("#")[0]
        .split("@")[-1]
        .partition(":")[0]
        .strip()
        .rstrip(".")
    )


def looks_like_ip(maybe_ip: str) -> bool:
    """Does the given str look like an IP address?"""
    if not maybe_ip[0].isdigit():
        return False

    try:
        socket.inet_aton(maybe_ip)
        return True
    except (AttributeError, UnicodeError):
        if IP_RE.match(maybe_ip):
            return True
    except OSError:
        pass

    return False
