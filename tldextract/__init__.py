"""Export tldextract's public interface."""

import pkg_resources

from .tldextract import extract, TLDExtract

try:
    __version__ = pkg_resources.get_distribution('tldextract').version  # pylint: disable=no-member
except pkg_resources.DistributionNotFound as _:
    __version__ = '(local)'
