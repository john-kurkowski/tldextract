"""`tldextract` accurately separates the gTLD or ccTLD (generic or country code
top-level domain) from the registered domain and subdomains of a URL.

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
"""

import re
import sys
from setuptools import setup

# I don't want to learn reStructuredText right now, so strip Markdown links
# that make pip barf.
LONG_DESCRIPTION_MD = __doc__
LONG_DESCRIPTION = re.sub(r'(?s)\[(.*?)\]\((http.*?)\)', r'\1', LONG_DESCRIPTION_MD)

INSTALL_REQUIRES = ["setuptools", "idna", "requests>=2.1.0", "requests-file>=1.4"]
if (2, 7) > sys.version_info:
    INSTALL_REQUIRES.append("argparse>=1.2.1")

setup(
    name="tldextract",
    version="2.0.2",
    author="John Kurkowski",
    author_email="john.kurkowski@gmail.com",
    description=("Accurately separate the TLD from the registered domain and"
                 "subdomains of a URL, using the Public Suffix List."),
    license="BSD License",
    keywords="tld domain subdomain url parse extract urlparse urlsplit public suffix list",
    url="https://github.com/john-kurkowski/tldextract",
    packages=['tldextract'],
    include_package_data=True,
    long_description=LONG_DESCRIPTION,
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Topic :: Utilities",
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
    ],
    entry_points={
        'console_scripts': [
            'tldextract = tldextract.cli:main', ]
    },
    install_requires=INSTALL_REQUIRES,
)
