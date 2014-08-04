from resourcesync_push.hub.hub import application

from webtest import TestApp
import unittest

app = TestApp(application)


class TestHubPublisher(unittest.TestCase):

    def test_publish_unknown(self):
        app.get("/heythere", status=404)

    def test_publish_get(self):
        app.get("/publish", status=405)

    def test_publish_invalid_content_type(self):
        app.post("/publish", content_type="", status=400)
        app.post("/publish", content_type="application/pdf", status=406)

    def test_publish_handle_invalid_push_request(self):
        data = "hub.mode=publish"
        app.post("/publish", content_type="application/x-www-form-urlencoded",
                 params=data, status=400)

    def test_publish_handle_push_request(self):
        data = "hub.mode=publish&hub.url=http://httpbin.org/get"
        app.post("/publish", content_type="application/x-www-form-urlencoded",
                 params=data, status=204)

    def test_publish_handle_invalid_resourcesync_request(self):
        data = ""
        app.post("/publish", content_type="application/xml",
                 params=data, status=400)
        # no link header
        data = "<url></url>"
        app.post("/publish", content_type="application/xml",
                 params=data, status=400)
        # bad link header
        data = "<url></url>"
        link = '<http://example.com/dataset1/change/>;rel="timegate",\
            <http://hub.example.org/pubsubhubbub/>;rel="memento"'
        app.post("/publish", content_type="application/xml",
                 params=data, status=400,
                 headers={'Link': link})

    def test_publish_handle_resourcesync_request(self):
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
        link = '<http://example.com/dataset1/change/>;rel="self",\
            <http://hub.example.org/pubsubhubbub/>;rel="hub"'
        app.post("/publish", content_type="application/xml",
                 params=payload, status=204,
                 headers={'Link': link})


class TestHubSubscriber(unittest.TestCase):

    def test_subscribe_get(self):
        app.get("/subscribe", status=405)

    def test_subscribe_invalid_content_type(self):
        app.post("/subscribe", content_type="", status=400)

    def test_subscribe_handle_invalid_push_request(self):
        data = "hub.mode=subscribe&hub.verify=async&\
            hub.topic=http://localhost/test&hub.callback=http://localhost"
        app.post("/subscribe",
                 content_type="application/x-www-form-urlencoded",
                 params=data, status=409)


class TestHubRegister(unittest.TestCase):

    def test_post(self):
        app.post("/register", status=405)

    def test_register(self):
        app.get("/register")


class TestHubRegisterSuccess(unittest.TestCase):

    def test_post(self):
        app.get("/registersuccess", status=405)

    def test_invalid_register_success(self):
        app.post("/registersuccess", status=400)

    def test_register_success(self):
        data = "topic_url=http://localhost"
        app.post("/registersuccess",
                 content_type="application/x-www-form-urlencoded",
                 params=data)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestHubPublisher))
    suite.addTest(unittest.makeSuite(TestHubSubscriber))
    suite.addTest(unittest.makeSuite(TestHubRegister))
    suite.addTest(unittest.makeSuite(TestHubRegisterSuccess))
    return suite
