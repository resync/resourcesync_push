import unittest
from resourcesync_push import ResourceSyncPuSH

resourcesync_push = ResourceSyncPuSH()


class TestResourceSyncPuSH(unittest.TestCase):

    def test_resourcesync_push_config(self):
        print("Reading hub config")
        resourcesync_push = ResourceSyncPuSH()
        resourcesync_push.get_config(classname='hub')
        assert resourcesync_push.config['my_url'] is not None

        print("Reading publisher config")
        resourcesync_push = ResourceSyncPuSH()
        resourcesync_push.get_config(classname='publisher')
        assert resourcesync_push.config['my_url'] is not None

        print("Reading subscriber config")
        resourcesync_push = ResourceSyncPuSH()
        resourcesync_push.get_config(classname='subscriber')
        assert resourcesync_push.config['my_url'] is not None

    def test_send_get(self):
        f = resourcesync_push.send("http://httpbin.org/get", method='GET')
        r = f.result()
        assert r.status_code == 200

    def test_send_post(self):
        f = resourcesync_push.send("http://httpbin.org/post", data="test")
        r = f.result()
        assert r.status_code == 200

    def test_respond(self):
        # test is covered in the inherited classes.
        assert True

    def test_get_topic_hub_url(self):
        link = '<http://example.com/dataset1/change/>;rel="self",\
            <http://hub.example.org/pubsubhubbub/>;rel="hub"'
        resourcesync_push = ResourceSyncPuSH()
        t, h = resourcesync_push.get_topic_hub_url(link)
        assert t == "http://example.com/dataset1/change/"
        assert h == "http://hub.example.org/pubsubhubbub/"

    def test_make_link_header(self):
        lh = resourcesync_push.make_link_header(hub_url="http://hub",
                                                topic_url="http://topic")
        lk = '<http://topic>;rel=self, <http://hub>;rel=hub'
        assert lh == lk

    def test_hub_config(self):
        resourcesync_push.get_config("hub")
        assert resourcesync_push.config.get('my_url') is not None

    def test_publisher_config(self):
        resourcesync_push.get_config("publisher")
        assert resourcesync_push.config.get('my_url') is not None
        assert resourcesync_push.config.get('topic_url') is not None
        assert resourcesync_push.config.get('hub_url') is not None

    def test_subscriber_config(self):
        resourcesync_push.get_config("subscriber")
        assert resourcesync_push.config.get('my_url') is not None


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestResourceSyncPuSH))
    return suite
