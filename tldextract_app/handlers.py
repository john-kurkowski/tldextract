from cStringIO import StringIO
import tldextract
import web

try:
    import json
except ImportError:
    from django.utils import simplejson as json

urls = (
    '/api/extract', 'Extract',
    '/api/re', 'TLDSet',
    '/test', 'Test',
)


class Extract:

    def GET(self):
        url = web.input(url='').url
        if not url:
            return web.webapi.badrequest()

        ext = tldextract.extract(url)._asdict()
        web.header('Content-Type', 'application/json')
        return json.dumps(ext) + '\n'


class TLDSet:

    def GET(self):
        extractor = tldextract.tldextract._get_tld_extractor()
        web.header('Content-Type', 'text/html; charset=utf-8')
        return '<br/>'.join(sorted(extractor.tlds))


class Test:

    def GET(self):
        stream = StringIO()
        tldextract.tldextract.run_tests(stream)
        return stream.getvalue()

app = web.application(urls, globals())
main = app.cgirun()
