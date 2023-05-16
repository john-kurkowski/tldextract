"tldextract helpers for testing and fetching remote resources."

import re
import socket
from urllib.parse import scheme_chars

IP_RE = re.compile(
    r"^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.)"
    r"{3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$"
)

scheme_chars_set = set(scheme_chars)


def lenient_netloc(url: str) -> str:
    """Extract the netloc of a URL-like string, similar to the netloc attribute
    returned by urllib.parse.{urlparse,urlsplit}, but extract more leniently,
    without raising errors."""
    return (
        _schemeless_url(url)
        .partition("/")[0]
        .partition("?")[0]
        .partition("#")[0]
        .rpartition("@")[-1]
        .partition(":")[0]
        .strip()
        .rstrip(".")
    )


def _schemeless_url(url: str) -> str:
    double_slashes_start = url.find("//")
    if double_slashes_start == 0:
        return url[2:]
    if (
        double_slashes_start < 2
        or not url[double_slashes_start - 1] == ":"
        or set(url[: double_slashes_start - 1]) - scheme_chars_set
    ):
        return url
    return url[double_slashes_start + 2 :]


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
