"""Export tldextract's public interface."""

from .tldextract import extract, TLDExtract

from . import _version
__version__: str = _version.version
