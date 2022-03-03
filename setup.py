""" `tldextract` accurately separates a URL's subdomain, domain, and public suffix,
using the Public Suffix List (PSL).

    >>> import tldextract
    >>> tldextract.extract('http://forums.news.cnn.com/')
    ExtractResult(subdomain='forums.news', domain='cnn', suffix='com')
    >>> tldextract.extract('http://forums.bbc.co.uk/') # United Kingdom
    ExtractResult(subdomain='forums', domain='bbc', suffix='co.uk')
    >>> tldextract.extract('http://www.worldbank.org.kg/') # Kyrgyzstan
    ExtractResult(subdomain='www', domain='worldbank', suffix='org.kg')

`ExtractResult` is a namedtuple, so it's simple to access the parts you want.

    >>> ext = tldextract.extract('http://forums.bbc.co.uk')
    >>> (ext.subdomain, ext.domain, ext.suffix)
    ('forums', 'bbc', 'co.uk')
    >>> # rejoin subdomain and domain
    >>> '.'.join(ext[:2])
    'forums.bbc'
    >>> # a common alias
    >>> ext.registered_domain
    'bbc.co.uk'

By default, this package supports the public ICANN TLDs and their exceptions.
You can optionally support the Public Suffix List's private domains as well.
"""

from setuptools import setup

INSTALL_REQUIRES = ["idna", "requests>=2.1.0", "requests-file>=1.4", "filelock>=3.0.8"]

setup(
    name="tldextract",
    author="John Kurkowski",
    author_email="john.kurkowski@gmail.com",
    description=(
        "Accurately separates a URL's subdomain, domain, and public suffix, "
        "using the Public Suffix List (PSL). By "
        "default, this includes the public ICANN TLDs and their "
        "exceptions. You can optionally support the Public Suffix "
        "List's private domains as well."
    ),
    license="BSD License",
    keywords="tld domain subdomain url parse extract urlparse urlsplit public suffix list publicsuffix publicsuffixlist",
    url="https://github.com/john-kurkowski/tldextract",
    packages=["tldextract"],
    include_package_data=True,
    python_requires=">=3.7",
    long_description=__doc__,
    long_description_content_type="text/markdown",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Topic :: Utilities",
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    entry_points={
        "console_scripts": [
            "tldextract = tldextract.cli:main",
        ]
    },
    setup_requires=["setuptools_scm"],
    use_scm_version={
        "write_to": "tldextract/_version.py",
    },
    install_requires=INSTALL_REQUIRES,
)
