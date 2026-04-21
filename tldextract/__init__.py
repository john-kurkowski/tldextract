"""Export tldextract's public interface."""

from . import _version
from .suffix_list import PslMetadata, SuffixListInfo
from .tldextract import ExtractResult, TLDExtract, extract, update

__version__: str = _version.version

__all__ = [
    "__version__",
    "extract",
    "ExtractResult",
    "PslMetadata",
    "SuffixListInfo",
    "TLDExtract",
    "update",
]
