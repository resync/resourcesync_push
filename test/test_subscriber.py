from resourcesync_push.subscriber.subscriber import application

from webtest import TestApp
import unittest


app = TestApp(application)


class TestSubscriber(unittest.TestCase):

    def test_bad_request(self):
        app.get('/', status=400)

    def test_unknown_url(self):
        # app = TestApp(application)
        app.get('/hello', status=404)

    def test_head_request(self):
        #self.app = TestApp(application)
        app.head("/", status=200)

    def test_subscription_verification(self):
        resp = app.get("/?hub.challenge=abc123")
        assert resp.body == "abc123"

    def test_process_subscription(self):
        params = {
            "topic_url": "http://localhost:9000/resourcesync/topic/test",
            "hub_url": "http://localhost:8000/subscribe"
        }
        content_type = "application/x-www-form-urlencoded"
        app.post("/",
                 params=params,
                 content_type=content_type)

    def test_process_resourcesync_payload(self):
        content_type = "application/xml"
        payload = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:rs="http://www.openarchives.org/rs/terms/">
  <rs:md capability="changelist"
         from="2013-01-02T00:00:00Z"
         until="2013-01-03T00:00:00Z"/>
  <url>
      <loc>http://example.com/res2.pdf</loc>
      <lastmod>2013-01-02T13:00:00Z</lastmod>
      <rs:md change="updated"/>
  </url>
  <url>
      <loc>http://example.com/res3.tiff</loc>
      <lastmod>2013-01-02T18:00:00Z</lastmod>
      <rs:md change="deleted"/>
  </url>
</urlset>"""
        app.post("/", params=payload, content_type=content_type)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestSubscriber))
    return suite
