from resync_push import ResyncPush

import time
import cPickle
import copy
import urlparse
import urllib


class Hub(ResyncPush):

    def __init__(self):
        ResyncPush.__init__(self, "hub")

    def save_subscriptions(self, subscriptions):
        'Save subscribers to disk as a dict'

        filename = self.subscribers_file

        print("saving" + filename)
        subscriptions = self.verify_lease(subscriptions)
        f = None
        try:
            f = open(filename, 'wb')
            cPickle.dump(subscriptions, f)
            print("saved subs to %s" % filename)
            print(subscriptions)
        except Exception, e:
            print(e)
        finally:
            if f:
                f.close()

    def read_subscriptions(self):
        "Read subscriber's list from file"

        filename = self.subscribers_file

        data = {}
        f = None
        try:
            # using 'r+b' file permissions here so that the
            # file gets created if there is none.
            f = open(filename, "r+b")
            data = cPickle.load(f)
        except Exception, e:
            print(e)
        finally:
            if f:
                f.close()
        return self.verify_lease(data)

    def verify_lease(self, subscriptions):
        """
        Loop through the dict of subscribers and del all the subscriptions
        that are past their lease time.
        """

        current_time = time.time()
        s = copy.deepcopy(subscriptions)
        for topic in list(subscriptions):
            for subscriber in subscriptions[topic]:
                if subscriptions[topic][subscriber] <= current_time:
                    del s[topic][subscriber]
        return s

    def baseN(self, num, b, numerals="0123456789abcdefghijklmnopqrstuvwxyz"):
        return ((num == 0) and "0") or \
            (self.baseN(num // b, b).lstrip("0") + numerals[num % b])


class HubPublisher(Hub):
    """
    Listens for requests from the publisher, determines if the payload is in
    PuSH or ResourceSync mode and publishes to the appropriate subscribers.
    """

    def __init__(self, env, start_response):
        Hub.__init__(self)
        self._env = env
        self._start_response = start_response

    def handle_push_request(self):
        # original PuSH spec mode
        query_st = self._env['wsgi.input'].read()
        query = urlparse.parse_qs(query_st)
        mode = query.get('hub.mode', [None])[0]
        self.push_url = query.get('hub.url', [None])[0]

        if not mode and not self.push_url:
            return self.respond(code=400,
                                msg="Bad Request: \
                                hub.url and hub.mode required.")

        if mode == "publish":
            future = self.send(self.push_url,
                               method='GET',
                               callback=self.publish_push_payload)
            while future.running():
                pass
            if future.done():
                return self.respond(code=204, msg="")
            else:
                return self.respond(code=400,
                                    msg="Error retrieving resource url:\
                                    %s" % self.push_url)
        else:
            return self.respond(code=400, msg="Unrecognised mode")

    def publish_push_payload(self, future_session, response):
        subscriptions = self.read_subscriptions()
        subscribers = subscriptions.get(self.push_url, None)
        if not subscribers:
            return self.respond(code=204, msg="")

        payload = response.content
        content_type = response.headers.get('content-type')
        headers = {
            'Content-Type': content_type,
            'Content-Length': str(len(payload))
        }
        for subscriber in subscribers:
            self.send(subscriber, data=payload, headers=headers)

        return

    def handle_resync_request(self, content_type="application/xml"):

        payload = None
        try:
            payload = self._env['wsgi.input'].read()
        except Exception as e:
            print(e)
            return self.respond(code=400, msg="Payload of size > 0 expected.")
        if not payload:
            return self.respond(code=400, msg="Payload of size > 0 expected.")

        link_header = self._env.get('HTTP_LINK', None)
        if not link_header:
            return self.respond(code=400,
                                msg="ResourceSync Link Headers required.")

        topic, hub_url = self.get_topic_hub_url(link_header)
        if not topic and not hub_url:
            return self.respond(code=400,
                                msg="ResourceSync Link header spec not met.")
        if self.trusted_topics and topic.strip() not in self.trusted_topics:
            return self.respond(code=403,
                                msg="Topic is not registered with the hub.")

        subscriptions = self.read_subscriptions()
        subscribers = subscriptions.get(topic, None)
        if not subscribers:
            return self.respond(code=204)

        headers = {
            'Content-Type': content_type,
            'Link': link_header,
            'Content-Length': str(len(payload))
        }
        for subscriber in subscribers:
            self.send(subscriber, data=payload, headers=headers)

        # success
        return self.respond(code=204)

    def handle(self):
        if not self._env.get('REQUEST_METHOD', None) == 'POST':
            return self.respond(code=403, msg='Method Not Allowed.')

        content_type = self._env.get('CONTENT_TYPE', None).lower()
        if not content_type:
            return self.respond(code=400,
                                msg="Invalid Content-Type value in header.")

        if content_type == "application/x-www-form-urlencoded":
            return self.handle_push_request()
        elif not self.mimetypes or content_type in self.mimetypes:
            return self.handle_resync_request(content_type=content_type)

        # error
        return self.respond(code=403,
                            msg="content-type header not recognised.")


class HubSubscriber(Hub):

    def __init__(self, env, start_response):
        Hub.__init__(self)
        self._env = env
        self._start_response = start_response

    def update_subscriber(self, topic, subscriber_url, lease,
                          mode="subscribe"):
        """
        Given the topic, subscriber url and lease time, this function
        adds a new subscriber and saves it.
        """

        subscriptions = {}
        subscriptions = self.read_subscriptions()

        if not subscriptions:
            subscriptions = {}
        try:
            subscriptions[topic]
        except Exception:
            subscriptions[topic] = {}

        if mode == "subscribe":
            subscriptions[topic][subscriber_url] = time.time() + lease
        elif mode == "unsubscribe":
            if subscriber_url in subscriptions[topic]:
                del subscriptions[topic][subscriber_url]

        self.save_subscriptions(subscriptions)
        return

    def subscribe(self, to_verify):
        """
        Handles Subscriptions. Checks the request, sends a challenge to
        the subscriber and verifies if the client relays the challenge back.
        Handles both subscriptions and unsubscriptions.
        """

        challenge = self.baseN(abs(hash(time.time())), 36)
        verify_token = to_verify.get('verify_token', None)
        payload = {
            'hub.mode': to_verify['mode'],
            'hub.topic': to_verify['topic'],
            'hub.challenge': challenge
        }

        if verify_token:
            payload['hub.verify_token'] = verify_token

        url = '?'.join([to_verify['callback'], urllib.urlencode(payload)])

        try:
            fut = self.send(url, method='GET')
            response = fut.result()
            payload = response.content

            if challenge in payload:
                if to_verify['mode'] == 'subscribe':
                    self.update_subscriber(to_verify['topic'],
                                           to_verify['callback'],
                                           to_verify['lease'],
                                           mode="subscribe")
                else:
                    self.update_subscriber(to_verify['topic'],
                                           to_verify['callback'],
                                           to_verify['lease'],
                                           mode="unsubscribe")
            else:
                return self.respond(code=409,
                                    msg="Subscription verification failed")

        except Exception:
            return self.respond(code=409,
                                msg="Subscription verification failed")

        # success
        return self.respond(code=204, msg="Subscription successful.")

    def handle(self):

        query_st = self._env['wsgi.input'].read()
        args = urlparse.parse_qs(query_st)

        mode = args.get('hub.mode', [None])[0]
        callback = args.get('hub.callback', [None])[0]
        topic = args.get('hub.topic', [None])[0]
        verify = args.get('hub.verify', [None])
        verify_token = args.get('hub.verify_token', [None])[0]
        lease = args.get('hub.lease_seconds', [2678400])[0]

        if not mode and not callback and not topic and not verify:
            return self.respond(code=400, msg="Bad request: Expected \
                'hub.mode', 'hub.callback', 'hub.topic', and 'hub.verify'")

        if not mode in ['subscribe', 'unsubscribe']:
            return self.respond(code=400, msg="Bad request: Unrecognized mode")

        # For now, only using the first preference of verify mode
        verify = verify[0]
        if not verify in ['sync', 'async']:
            return self.respond(code=400,
                                msg="Bad request: \
                                Unsupported verification mode")

        to_verify = {'mode': mode,
                     'callback': callback,
                     'topic': topic,
                     'verify_token': verify_token,
                     'lease': lease}
        # async
        # FIXME: implement sync
        return self.subscribe(to_verify)


class HubForm(Hub):
    def __init__(self, env, start_response):
        Hub.__init__(self)
        self._env = env
        self._start_response = start_response

    def handle(self):
        self._start_response("200 OK", [('Content-Type', 'text/html')])
        return ["form"]


def application(env, start_response):
    req_path = env.get('PATH_INFO', "/")

    if req_path == "/publish":
        p = HubPublisher(env, start_response)
        return p.handle()
    elif req_path == "/subscribe":
        s = HubSubscriber(env, start_response)
        return s.handle()
    elif req_path == "/":
        h = HubForm(env, start_response)
        return h.handle()
    else:
        start_response("404 Not Found", [('Content-Type', 'text/html')])
        return ["Requested resource not found."]
