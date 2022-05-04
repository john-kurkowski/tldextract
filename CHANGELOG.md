# tldextract Changelog

After upgrading, update your cache file by deleting it or via `tldextract
--update`.

## 3.3.0 (2022-05-04)

* Features
  * Add CLI flag `--suffix_list_url` to set the suffix list URL(s) or source file(s) ([#197](https://github.com/john-kurkowski/tldextract/issues/197))
  * Add CLI flag `--no_fallback_to_snapshot` to not fall back to the snapshot ([#260](https://github.com/john-kurkowski/tldextract/issues/260))
  * Add alias `--include_psl_private_domains` for CLI flag `--private_domains`
* Bugfixes
  * Handle more internationalized domain name dots ([#253](https://github.com/john-kurkowski/tldextract/issues/253))
* Misc.
  * Update bundled snapshot
  * Add basic CLI test coverage

## 3.2.1 (2022-04-11)

* Bugfixes
  * Fix incorrect namespace used for caching function returns ([#258](https://github.com/john-kurkowski/tldextract/issues/258))
  * Remove redundant encode ([`6e2c0e0`](https://github.com/john-kurkowski/tldextract/commit/6e2c0e0))
  * Remove redundant lowercase ([`226bfc2`](https://github.com/john-kurkowski/tldextract/commit/226bfc2))
  * Remove unused `try`/`except` path ([#255](https://github.com/john-kurkowski/tldextract/issues/255))
  * Add types to the private API (disallow untyped calls and defs) ([#256](https://github.com/john-kurkowski/tldextract/issues/256))
  * Rely on `python_requires` instead of runtime check ([#247](https://github.com/john-kurkowski/tldextract/issues/247))
* Docs
  * Fix docs with updated types
  * Fix link in Travis CI badge ([#248](https://github.com/john-kurkowski/tldextract/issues/248))
  * Rewrite documentation intro
  * Remove unnecessary subheading
  * Unify case

## 3.2.0 (2022-02-20)

* Features
    * Add types to the public API ([#244](https://github.com/john-kurkowski/tldextract/issues/244))
* Bugfixes
    * Add support for Python 3.10 ([#246](https://github.com/john-kurkowski/tldextract/issues/246))
    * Drop support for EOL Python 3.6 ([#246](https://github.com/john-kurkowski/tldextract/issues/246))
    * Remove py2 tag from wheel ([#245](https://github.com/john-kurkowski/tldextract/issues/245))
    * Remove extra backtick in README ([#240](https://github.com/john-kurkowski/tldextract/issues/240))

## 3.1.2 (2021-09-01)

* Misc.
    * Only run pylint in Tox environments, i.e. CI, not by default in tests ([#230](https://github.com/john-kurkowski/tldextract/issues/230))

## 3.1.1 (2021-08-27)

* Bugfixes
    * Support Python 3.9
    * Drop support for EOL Python 3.5

## 3.1.0 (2020-11-22)

* Features
    * Prefer to cache in XDG cache directory in user folder, vs. in Python install folder ([#213](https://github.com/john-kurkowski/tldextract/issues/213))
* Bugfixes
    * Fix `AttributeError` on `--update` ([#215](https://github.com/john-kurkowski/tldextract/issues/215))

## 3.0.2 (2020-10-24)

* Bugfixes
    * Catch permission error when making cache dir, as well as cache file ([#211](https://github.com/john-kurkowski/tldextract/issues/211))

## 3.0.1 (2020-10-21)

* Bugfixes
    * Fix `tlds` property `AttributeError` ([#210](https://github.com/john-kurkowski/tldextract/issues/210))
    * Allow `include_psl_private_domains` in global `extract` too ([#210](https://github.com/john-kurkowski/tldextract/issues/210))

## 3.0.0 (2020-10-20)

No changes since 3.0.0.rc1.

## 3.0.0.rc1 (2020-10-12)

This release fixes the long standing bug that public and private suffixes were
generated separately and could not be switched at runtime,
[#66](https://github.com/john-kurkowski/tldextract/issues/66).

* Breaking Changes
    * Rename `cache_file` to `cache_dir` as it is no longer a single file but a directory ([#207](https://github.com/john-kurkowski/tldextract/issues/207))
    * Rename CLI arg also, from `--cache_file` to `--cache_dir`
    * Remove Python 2.7 support
* Features
    * Can pass `include_psl_private_domains` on call, not only on construction
    * Use filelocking to support multi-processing and multithreading environments
* Bugfixes
    * Select public or private suffixes at runtime ([#66](https://github.com/john-kurkowski/tldextract/issues/66))
* Removals
    * Do not `debug` log the diff during update

## 2.2.3 (2020-08-05)

* Bugfixes
    * Fix concurrent access to cache file when using tldextract in multiple threads ([#146](https://github.com/john-kurkowski/tldextract/pull/146))
    * Relocate version number, to avoid costly imports ([#187](https://github.com/john-kurkowski/tldextract/pull/187))
    * Catch `IndexError` caused by upstream punycode bug ([#200](https://github.com/john-kurkowski/tldextract/pull/200))
    * Drop support for EOL Python 3.4 ([#186](https://github.com/john-kurkowski/tldextract/pull/186))
    * Explain warning better

## 2.2.2 (2019-10-15)

* Bugfixes
    * Catch file not found
    * Use pkgutil instead of pkg_resources ([#163](https://github.com/john-kurkowski/tldextract/pull/163))
    * Performance: avoid recomputes, a regex, and a partition
* Misc.
    * Update LICENSE from GitHub template
    * Fix warning about literal comparison
    * Modernize testing ([#177](https://github.com/john-kurkowski/tldextract/issues/177))
        * Use the latest pylint that works in Python 2
        * Appease pylint with the new rules
        * Support Python 3.8-dev

## 2.2.1 (2019-03-05)

* Bugfixes
    * Ignore case on punycode prefix check ([#133](https://github.com/john-kurkowski/tldextract/issues/133))
    * Drop support for EOL Python 2.6 ([#152](https://github.com/john-kurkowski/tldextract/issues/152))
    * Improve sundry doc and README bits

## 2.2.0 (2017-10-26)

* Features
    * Add `cache_fetch_timeout` kwarg and `TLDEXTRACT_CACHE_TIMEOUT` env var ([#139](https://github.com/john-kurkowski/tldextract/issues/139))
* Bugfixes
    * Work around `pkg_resources` missing, again ([#137](https://github.com/john-kurkowski/tldextract/issues/137))
    * Always close sessions ([#140](https://github.com/john-kurkowski/tldextract/issues/140))

## 2.1.0 (2017-05-24)

* Features
    * Add `fqdn` convenience property ([#129](https://github.com/john-kurkowski/tldextract/issues/129))
    * Add `ipv4` convenience property ([#126](https://github.com/john-kurkowski/tldextract/issues/126))

## 2.0.3 (2017-05-20)

* Bugfixes
    * Switch to explicit Python version check ([#124](https://github.com/john-kurkowski/tldextract/issues/124))
* Misc.
    * Document public vs. private domains
    * Document support for Python 3.6

## 2.0.2 (2016-10-16)

* Misc.
    * Release as a universal wheel ([#110](https://github.com/john-kurkowski/tldextract/issues/110))
    * Consolidate test suite running with tox ([#104](https://github.com/john-kurkowski/tldextract/issues/104))

## 2.0.1 (2016-04-25)

* Bugfixes
    * Relax required `requests` version: >= 2.1 ([#98](https://github.com/john-kurkowski/tldextract/issues/98))
* Misc.
    * Include tests in release source tarball ([#97](https://github.com/john-kurkowski/tldextract/issues/97))

## 2.0.0 (2016-04-21)

No changes since 2.0rc1.

## 2.0rc1 (2016-04-04)

This release focuses on shedding confusing code branches & deprecated cruft.

* Breaking Changes
    * Renamed/changed the type of `TLDExtract` constructor param
      `suffix_list_url`
        * It used to take a `str` or iterable. Its replacement,
          `suffix_list_urls` only takes an iterable. This better communicates
          that it tries a _sequence_ of URLs, in order. To only try 1 URL, pass
          an iterable with exactly 1 URL `str`.
    * Serialize the local cache of the remote PSL as JSON (no more `pickle`) - [#81](https://github.com/john-kurkowski/tldextract/issues/81)
        * This should be a transparent upgrade for most users.
        * However, if you're configured to _only_ read from your local cache
          file, no other sources or fallbacks, the new version will be unable
          to read the old cache format, and an error will be raised.
    * Remove deprecated code
        * `TLDExtract`'s `fetch` param. To disable live HTTP requests for the
          latest PSL, instead pass `suffix_list_urls=None`.
        * `ExtractResult.tld` property. Use `ExtractResult.suffix` instead.
    * Moved code
        * Split `tldextract.tldextract` into a few files.
            * The official public interface of this package comes via `import
              tldextract`. But if you were relying on direct import from
              `tldextract.tldextract` anyway, those imports may have moved.
            * You can run the package `python -m tldextract` for the same
              effect as the included `tldextract` console script. This used to
              be `python -m tldextract.tldextract`.
* Misc.
    * Use `requests` instead of `urllib` - [#89](https://github.com/john-kurkowski/tldextract/issues/89)
        * As a side-effect, this fixes [#93](https://github.com/john-kurkowski/tldextract/pull/93).

## 1.7.5 (2016-02-07)

* Bugfixes
    * Support possible gzipped PSL response - [#88](https://github.com/john-kurkowski/tldextract/pull/88)

## 1.7.4 (2015-12-26)

* Bugfixes
    * Fix potential for `UnicodeEncodeError` with info log - [#85](https://github.com/john-kurkowski/tldextract/pull/85)

## 1.7.3 (2015-12-12)

* Bugfixes
    * Support IDNA2008 - [#82](https://github.com/john-kurkowski/tldextract/pull/82)
* Misc.
    * Ease running scripts during local development

## 1.7.2 (2015-11-28)

* Bugfixes
    * Domain parsing fails with trailing spaces - [#75](https://github.com/john-kurkowski/tldextract/pull/75)
    * Update to latest, direct PSL links - [#77](https://github.com/john-kurkowski/tldextract/pull/77)
* Misc.
    * Update bundled PSL snapshot
    * Require requirements.txt for local development
    * Enforce linting via the test suite - [#79](https://github.com/john-kurkowski/tldextract/pull/79)
    * Switch to py.test runner - [#80](https://github.com/john-kurkowski/tldextract/pull/80)
    * No longer distribute tests. No mention of `test_suite` in setup.py. CI is
      handled centrally now, on this project's GitHub.

## 1.7.1 (2015-08-22)

Fix publishing mistake with 1.7.0.

## 1.7.0 (2015-08-22)

* Features
    * Can include PSL's private domains on CLI with `--private_domains` boolean flag
* Bugfixes
    * Improved support for multiple Punycode (or Punycode-looking) parts of a URL
        * Mixed in/valid
        * Mixed encodings
    * Fix `ExtractResult._asdict` on Python 3.4. This should also save space,
      as `__dict__` is not created for each `ExtractResult` instance.

## 1.6 (2015-03-22)

* Features
    * Pass `extra_suffixes` directly to constructor
* Bugfixes
    * Punycode URLs were returned decoded, rather than left alone
    * Things that look like Punycode to tldextract, but aren't, shouldn't raise
    * Print unified diff to debug log, rather than inconsistent stderr

## 1.5.1 (2014-10-13)

* Bugfixes
    * Missing setuptools dependency
    * Avoid u'' literal for Python 3.0 - 3.2 compatibility. Tests will still fail though.

## 1.5 (2014-09-08)

* Bugfixes
    * Exclude PSL's private domains by default - [#19](https://github.com/john-kurkowski/tldextract/pull/19)
        * This is a **BREAKING** bugfix if you relied on the PSL's private
          domains
        * Revert to old behavior by setting `include_psl_private_domains=True`
    * `UnicodeError` for inputs that looked like an IP

## 1.4 (2014-06-01)

* Features
    * Support punycode inputs
* Bugfixes
    * Fix minor Python 3 unicode errors

## 1.3.1 (2013-12-16)

* Bugfixes
    * Match PSL's GitHub mirror rename, from mozilla-central to gecko-dev
    * Try Mozilla's PSL SPOT first, then the mirror

## 1.3 (2013-12-08)

* Features
    * Specify your own PSL url/file with `suffix_list_url` kwarg
    * `fallback_to_snapshot` kwarg - defaults to True
* Deprecations
    * `fetch` kwarg

## 1.2 (2013-07-07)

* Features
    * Better CLI
    * Cache env var support
    * Python 3.3 support
    * New aliases `suffix` and `registered_domain`
* Bugfixes
    * Fix dns root label

## 1.1 (2012-03-22)

* Bugfixes
    * Reliable logger name
    * Forgotten `import sys`
