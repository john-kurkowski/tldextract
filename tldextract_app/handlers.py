import tldextract
import web

try:
  import json
except ImportError:
  from django.utils import simplejson as json

urls = (
        '/api/extract', 'Extract',
    )

class Extract:
    def GET(self):
        url = web.input('url').values()[0]
        try:
            ext = tldextract.extract(url)
        except ValueError, e:
            return web.webapi.badrequest()

        web.header('Content-Type', 'application/json')
        return json.dumps(ext) + '\n'

app = web.application(urls, globals())
main = app.cgirun()

