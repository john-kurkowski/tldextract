'''web.py handlers for making a JSON-over-HTTP API around tldextract.'''

import json

# pylint: disable=import-error
import tldextract
import web

URLS = (
    '/api/extract', 'Extract',
    '/api/re', 'TLDSet',
    '/test', 'Test',
)


class Extract(object):

    def GET(self): # pylint: disable=invalid-name,no-self-use
        url = web.input(url='').url
        if not url:
            return web.webapi.badrequest()

        ext = tldextract.extract(url)._asdict()
        web.header('Content-Type', 'application/json')
        return json.dumps(ext) + '\n'


class TLDSet(object):

    def GET(self): # pylint: disable=invalid-name,no-self-use
        web.header('Content-Type', 'text/html; charset=utf-8')
        return '<br/>'.join(sorted(tldextract.tldextract.TLD_EXTRACTOR.tlds))


APP = web.application(URLS, globals())
main = APP.cgirun()
