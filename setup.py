import re
from setuptools import setup
import tldextract

# I don't want to learn reStructuredText right now, so strip Markdown links
# that make pip barf.
long_description_markdown = tldextract.tldextract.__doc__
long_description = re.sub(r'(?s)\[(.*?)\]\((http.*?)\)', r'\1', long_description_markdown)

setup(
    name = "tldextract",
    version = tldextract.__version__,
    author = "John Kurkowski",
    author_email = "john.kurkowski@gmail.com",
    description = ("Accurately separate the TLD from the registered domain and subdomains of a URL, using the Public Suffix List."),
    license = "BSD License",
    keywords = "tld domain subdomain url parse extract urlparse urlsplit public suffix list",
    url = "https://github.com/john-kurkowski/tldextract",
    packages = ['tldextract', 'tldextract.tests'],
    include_package_data = True,
    long_description = long_description,
    classifiers = [
        "Development Status :: 5 - Production/Stable",
        "Topic :: Utilities",
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python :: 2.5",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
    ],
    test_suite = 'tldextract.tests.all.test_suite',
)

