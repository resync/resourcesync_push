"""
A Web Sockets implementation of the Hub. The connection between
the subscriber and the hub is implemented using web sockets.
"""

import uwsgi
from resync_push import ResyncPush

import time
import cPickle
import copy
import urlparse
import urllib
import os
import json


class HubPublisher(Hub):
    """
    Listens for requests from the publisher, determines if the payload is in
    PuSH or ResourceSync mode and publishes to the appropriate subscribers.
    """

    def __init__(self, env, start_response):
        Hub.__init__(self)
        self._env = env
        self._start_response = start_response

    def handle_resync_request(self, content_type="application/xml"):
        """
        ResourceSync payload. Gets the topic and hub url from the link
        header and broadcasts to the subscribers.
        """

        payload = None
        try:
            payload = self._env['wsgi.input'].read()
        except Exception as err:
            print(err)
            #return self.respond(code=400, msg="Payload of size > 0 expected.")
        if not payload:
            return self.respond(code=400, msg="Payload of size > 0 expected.")

        link_header = self._env.get('HTTP_LINK', None)
        if not link_header:
            return self.respond(code=400,
                                msg="ResourceSync Link Headers required.")

        topic, hub_url = ResyncPush.get_topic_hub_url(link_header)
        if not topic and not hub_url:
            return self.respond(code=400,
                                msg="ResourceSync Link header spec not met.")
        if self.trusted_topics and topic.strip() not in self.trusted_topics:
            return self.respond(code=403,
                                msg="Topic is not registered with the hub.")

        ws_publish(topic, payload)

        # success
        return self.respond(code=204)

    def handle(self):
        """
        Determines if the request is a PuSH or a ResourceSync request based
        on content-type header and processes appropriately.
        """

        if not self._env.get('REQUEST_METHOD', None) == 'POST':
            return self.respond(code=405, msg='Method Not Allowed.')

        content_type = self._env.get('CONTENT_TYPE', None).lower()
        if not content_type:
            return self.respond(code=400,
                                msg="Invalid Content-Type value in header.")

        if not self.mimetypes or content_type in self.mimetypes:
            return self.handle_resync_request(content_type=content_type)

        # error
        return self.respond(code=406,
                            msg="content-type header not recognised.")

    def ws_publish(self, topic, payload):
        subscribers = HubSubscriber.subscribers.get(topic, [])
        for subscriber in subscribers:
            uwsgi.websocket_send(payload)
        return


class HubSubscriber(Protocol):

    subscribers = {}

    def __init__(self):
        self.waiting_subscriptions = {}

    def base_n(self, num, bits,
               numerals="0123456789abcdefghijklmnopqrstuvwxyz"):
        """
        Creates a unique hash for subscription verification.
        """

        return ((num == 0) and "0") or \
            (self.base_n(num // bits, bits).lstrip("0") + numerals[num % bits])

    def handle(self, data):

        j_data = {}
        try:
            j_data = json.loads(data)
        except Exception as e:
            uwsgi.websocket_send("Error: %s" % e)
            return

        mode = j_data.get('hub.mode', None)
        topic = j_data.get('hub.topic', None)
        res_challenge = j_data.get("hub.challenge", None)

        if res_challenge:
            self.ws_verify_challenge(res_challenge)
        else:
            self.ws_verify_subscription(mode, topic)
        return

    def ws_verify_subscription(self, mode, topic):
        if not mode or not topic:
            uwsgi.websocket_send("Bad request: Expected \
                'hub.mode', 'hub.topic'")
            return

        if not mode in ['subscribe', 'unsubscribe']:
            uwsgi.websocket_send("Bad request: Unrecognized mode")
            return

        if mode == "unsubscribe":
            self.subscribers[topic].remove(self)
            return

        challenge = base_n(abs(hash(time.time())), 36)
        payload = {
            "hub.mode": mode,
            "hub.topic": topic,
            "hub.challenge": challenge
        }
        print("Subscription request received for topic: %s" % topic)
        print("Sending verification challenge")
        uwsgi.websocket_send(json.dumps(payload))
        self.waiting_subscriptions[challenge] = {
            'topic': topic,
            'connection': self
        }
        return

    def ws_verify_challenge(self, challenge):
        sub = self.waiting_subscriptions[challenge]
        t = self.subscribers.get(sub['topic'], None)
        if not t:
            self.subscribers[sub['topic']] = []
        self.subscribers[sub['topic']].append(sub['connection'])
        print("Subscription verified.")
        del self.waiting_subscriptions[challenge]
        return


def application(env, start_response):
    """
    WSGI entry point to the hub.
    """
    req_path = env.get('PATH_INFO', "/")

    if req_path == "/publish":
        publisher = HubPublisher(env, start_response)
        return publisher.handle()
    elif req_path == "/subscribe":
        subscriber = HubSubscriber(env, start_response)
        uwsgi.websocket_handshake(env['HTTP_SEC_WEBSOCKET_KEY'],
                                  env.get('HTTP_ORIGIN', '')
                                  )
        while True:
            msg = uwsgi.websocket_recv()
            print(msg)
            #uwsgi.websocket_send(msg)
            subscriber.handle(msg)
    else:
        start_response("404 Not Found", [('Content-Type', 'text/html')])
        return ["Requested resource not found."]
