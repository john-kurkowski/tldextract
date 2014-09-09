# tldextract Changelog

After upgrading, update your cache file by deleting it or via `tldextract
--update`.

## 1.5 (2014-09-08)

* Bugfixes
    * Exclude PSL's private domains by default - #19
        * This is a **BREAKING** bugfix if you relied on the PSL's private
          domains
        * Revert to old behavior by setting `use_psl_private_domains=True`
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
