"""Export tldextract's public interface."""

try:
    import pkg_resources
except ImportError:
    class pkg_resources(object):  # pylint: disable=invalid-name

        """Fake pkg_resources interface which falls back to getting resources
        inside `tldextract`'s directory.
        """
        @classmethod
        def resource_stream(cls, _, resource_name):
            moddir = os.path.dirname(__file__)
            path = os.path.join(moddir, resource_name)
            return open(path)

from .tldextract import extract, TLDExtract

try:
    __version__ = pkg_resources.get_distribution('tldextract').version  # pylint: disable=no-member
except pkg_resources.DistributionNotFound as _:
    __version__ = '(local)'
