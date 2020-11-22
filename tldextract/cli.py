"""tldextract CLI"""


import argparse
import logging
import sys

from ._version import version as __version__
from .tldextract import TLDExtract


def main():
    """tldextract CLI main command."""
    logging.basicConfig()

    parser = argparse.ArgumentParser(
        prog="tldextract", description="Parse hostname from a url or fqdn"
    )

    parser.add_argument(
        "--version", action="version", version="%(prog)s " + __version__
    )
    parser.add_argument(
        "input", metavar="fqdn|url", type=str, nargs="*", help="fqdn or url"
    )

    parser.add_argument(
        "-u",
        "--update",
        default=False,
        action="store_true",
        help="force fetch the latest TLD definitions",
    )
    parser.add_argument(
        "-c", "--cache_dir", help="use an alternate TLD definition caching folder"
    )
    parser.add_argument(
        "-p",
        "--private_domains",
        default=False,
        action="store_true",
        help="Include private domains",
    )

    args = parser.parse_args()

    obj_kwargs = {
        "include_psl_private_domains": args.private_domains,
    }
    if args.cache_dir:
        obj_kwargs["cache_dir"] = args.cache_dir

    tld_extract = TLDExtract(**obj_kwargs)

    if args.update:
        tld_extract.update(True)
    elif not args.input:
        parser.print_usage()
        sys.exit(1)
        return

    for i in args.input:
        print(" ".join(tld_extract(i)))
