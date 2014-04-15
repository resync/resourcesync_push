from resourcesync_push.publisher.publisher import application

from webtest import TestApp
import unittest


app = TestApp(application)


class TestPublisher(unittest.TestCase):

    def test_get_request(self):
        app.get('/', status=403)

    def test_unknown_url(self):
        # app = TestApp(application)
        app.get('/hello', status=404)

    def test_head_request(self):
        #self.app = TestApp(application)
        app.head("/", status=200)

    def test_no_content_type(self):
        app.post("/", status=400)

    def test_unsuppo_content_type(self):
        app.post("/", status=406, content_type="application/pdf")

    def test_no_payload_post(self):
        app.post("/", status=400, content_type="application/xml")

    def test_valid_request(self):
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
        app.post("/", content_type="application/xml", params=payload)

    def test_topic_url(self):
        from resourcesync_push import ResourceSyncPuSH

        resourcesync_push = ResourceSyncPuSH()
        resourcesync_push.get_config(classname='publisher')
        app.get(resourcesync_push.topic_url, status=204)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestPublisher))
    return suite
