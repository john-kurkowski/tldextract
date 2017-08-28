"""Export tldextract's public interface."""

import os

try:
    import pkg_resources
    __version__ = pkg_resources.get_distribution('tldextract').version  # pylint: disable=no-member
except ImportError:
    __version__ = '(local)'
except pkg_resources.DistributionNotFound:
    __version__ = '(local)'

from .tldextract import extract, TLDExtract
