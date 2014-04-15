from twisted.web import error, http, server
from twisted.internet.protocol import Protocol, Factory

from rspush import ResourceSyncPuSH

import time
import json


def baseN(num, b, numerals="0123456789abcdefghijklmnopqrstuvwxyz"):
    return ((num == 0) and "0") or \
        (baseN(num // b, b).lstrip("0") + numerals[num % b])


class PublishResource(ResourceSyncPuSH):
    """
    Listens for requests from the publisher, determines if the payload is in
    PuSH or ResourceSync mode and publishes to the appropriate subscribers.
    """

    def handle_resync_request(self, request, content_type="application/xml"):
        # resource sync mode
        link_header = request.getHeader("link")

        if link_header:
            #print("Source link header present.")
            #print("Link Header: \n%s" % link_header)
            pass
        else:
            request.setResponseCode(http.BAD_REQUEST)
            return "400 Bad Request: ResourceSync requires a link header."

        links = self.parse_links(link_header)
        topic = self.get_uri_for_rel(links, "self")

        payload = request.content.read()
        print("payload: " + payload)

        if not topic or not payload:
            request.setResponseCode(http.BAD_REQUEST)
            return "400 Bad Request: \
                ResourceSync requires a topic and payload."

        #print("%d bytes of data received from publisher for topic %s." % (len(payload), topic))

        #publish(topic, data=payload,
        #        resource_sync_mode=True, mimetype=content_type)
        ws_publish(topic, data=payload, link_header=link_header)
        request.setResponseCode(http.ACCEPTED)
        return "200 Success"

    isLeaf = True

    def render_POST(self, request):

        self.handle_resync_request(request)


def ws_publish(topic, data=None, link_header=None):
    """
    Publishes to the subscribers using WebSockets. Supports the ResourceSync
    spec only. For ResourceSync mode, the content to publish is already
    available in data and it is just relayed to the subscribers.
    """

    subscribers = WsHubProtocol.subscribers.get(topic, [])

    print(data)

    if len(subscribers):
        #print "Publishing to %d subscribers." % (len(subscribers))
        try:
            for subscriber in subscribers:
                subscriber.transport.write(data)
        except error.Error, e:
            print e


class WsHubProtocol(Protocol):

    subscribers = {}

    def __init__(self):
        self.waiting_subscriptions = {}

    def connectionMade(self):
        return

    def dataReceived(self, data):

        j_data = {}
        try:
            j_data = json.loads(data)
        except Exception as e:
            self.transport.write("Error: %s" % e)
            self.transport.loseConnection()
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
            self.transport.write("Bad request: Expected \
                'hub.mode', 'hub.topic'")
            self.transport.loseConnection()
            return

        if not mode in ['subscribe', 'unsubscribe']:
            self.transport.write("Bad request: Unrecognized mode")
            self.transport.loseConnection()
            return

        if mode == "unsubscribe":
            WsHubProtocol.subscribers[topic].remove(self)
            self.transport.loseConnection()
            return

        challenge = baseN(abs(hash(time.time())), 36)
        payload = {
            "hub.mode": mode,
            "hub.topic": topic,
            "hub.challenge": challenge
        }
        print("Subscription request received for topic: %s" % topic)
        print("Sending verification challenge")
        self.transport.write(json.dumps(payload))
        self.waiting_subscriptions[challenge] = {
            'topic': topic,
            'connection': self
        }
        return

    def ws_verify_challenge(self, challenge):
        sub = self.waiting_subscriptions[challenge]
        t = WsHubProtocol.subscribers.get(sub['topic'], None)
        if not t:
            WsHubProtocol.subscribers[sub['topic']] = []
        WsHubProtocol.subscribers[sub['topic']].append(sub['connection'])
        print("Subscription verified.")
        del self.waiting_subscriptions[challenge]
        return


class WsHubResource(Factory):

    def buildProtocol(self, addr):
        return WsHubProtocol()


class SizeLimitingRequest(server.Request):
    """
    Overrides handleContentChunk in the Twisted request class
    to truncate all POST requests from the publisher with a payload
    greater than 2MB.

    A simple check to prevent abuse of the hub resources by rouge clients.
    """

    def handleContentChunk(self, data):
        if self.content.tell() + len(data) > 2097152:
            self.channel.transport.write(b"HTTP/1.1 413 \
                                         Request Entity too large.\r\n\r\n")
            self.channel.transport.loseConnection()
        return server.Request.handleContentChunk(self, data)
