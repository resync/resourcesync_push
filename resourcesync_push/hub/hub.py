"""The Hub resource."""

from resourcesync_push import ResourceSyncPuSH

import time
import cPickle
import copy
import urlparse
import urllib
import os


class Hub(ResourceSyncPuSH):
    """
    The base class for hub resources.
    """

    def __init__(self):
        ResourceSyncPuSH.__init__(self)
        self.get_config("hub")

    def save_subscriptions(self, subscriptions):
        'Save subscribers to disk as a dict'

        filename = self.config['subscribers_file']

        subscriptions = self.verify_lease(subscriptions)
        sub_file = None
        try:
            sub_file = open(filename, 'wb')
            cPickle.dump(subscriptions, sub_file)
        except IOError as err:
            print(err)
        finally:
            if sub_file:
                sub_file.close()

    def read_subscriptions(self):
        "Read subscriber's list from file"

        filename = self.config['subscribers_file']

        data = {}
        sub_file = None
        try:
            # using 'r+b' file permissions here so that the
            # file gets created if there is none.
            sub_file = open(filename, "r+b")
            data = cPickle.load(sub_file)
        except IOError as err:
            print(err)
        finally:
            if sub_file:
                sub_file.close()
        return self.verify_lease(data)

    def verify_lease(self, subscriptions):
        """
        Loop through the dict of subscribers and del all the subscriptions
        that are past their lease time.
        """

        current_time = time.time()
        subs = copy.deepcopy(subscriptions)
        for topic in list(subscriptions):
            for subscriber in subscriptions[topic]:
                if subscriptions[topic][subscriber] <= current_time:
                    del subs[topic][subscriber]
        return subs

    def base_n(self, num, bits,
               numerals="0123456789abcdefghijklmnopqrstuvwxyz"):
        """
        Creates a unique hash for subscription verification.
        Taken from: https://github.com/progrium/wolverine/blob/master/\
            miyamoto/pubsub.py
        """

        return ((num == 0) and "0") or \
            (self.base_n(num // bits, bits).lstrip("0") + numerals[num % bits])


class HubPublisher(Hub):
    """
    Listens for requests from the publisher, determines if the payload is in
    PuSH or ResourceSync mode and publishes to the appropriate subscribers.
    """

    def __init__(self, env, start_response):
        Hub.__init__(self)
        self._env = env
        self._start_response = start_response
        self.push_url = ""

    def handle_push_request(self):
        """
        Original PuSH spec mode. Fetches the resource in the hub.url param
        and starts the broadcast of the data to the subscribers asynchronously.
        """

        query_st = self._env['wsgi.input'].read()
        query = urlparse.parse_qs(query_st)
        mode = query.get('hub.mode', [None])[0]
        self.push_url = query.get('hub.url', [None])[0]

        if not mode or not self.push_url:
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

        return self.respond(code=400, msg="Unrecognised mode")

    def publish_push_payload(self, future_session, response):
        """
        The async callback method for the PuSH payload. Broadcasts the
        payload to the subscribers.
        """

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

    def handle_resourcesync_request(self, content_type="application/xml"):
        """
        ResourceSync payload. Gets the topic and hub url from the link
        header and broadcasts to the subscribers.
        """

        payload = self._env['wsgi.input'].read()
        if not payload:
            return self.respond(code=400, msg="Payload of size > 0 expected.")

        link_header = self._env.get('HTTP_LINK', None)
        if not link_header:
            return self.respond(code=400,
                                msg="ResourceSync Link Headers required.")

        topic, hub_url = ResourceSyncPuSH.get_topic_hub_url(link_header)
        if not topic and not hub_url:
            return self.respond(code=400,
                                msg="ResourceSync Link header spec not met.")
        if self.config['trusted_topics'] and \
                topic.strip() not in self.config['trusted_topics']:
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

        self.log_msg['msg'].append("Posting change notification to %s \
                                   subscriber(s)" % len(subscribers))
        self.log_msg['msg'].append("ResourceSync Payload size: %s" %
                                   str(len(payload)))
        self.log_msg['link_header'] = link_header

        self.log()

        for subscriber in subscribers:
            self.send(subscriber, data=payload, headers=headers)

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

        if content_type == "application/x-www-form-urlencoded":
            return self.handle_push_request()
        elif not self.config['mimetypes'] or \
                content_type in self.config['mimetypes']:
            return self.handle_resourcesync_request(content_type=content_type)

        # error
        return self.respond(code=406,
                            msg="content-type header not recognised.")


class HubSubscriber(Hub):
    """
    Listens for and processes subscription requests.
    """

    def __init__(self, env, start_response):
        Hub.__init__(self)
        self._env = env
        self._start_response = start_response

    def update_subscriber(self, topic, subscriber_url, lease,
                          mode="subscribe"):
        """
        Given the topic, subscriber url and lease time, this method
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
        Handles both subscription and unsubscription requests.
        """

        challenge = self.base_n(abs(hash(time.time())), 36)
        payload = {
            'hub.mode': to_verify['mode'],
            'hub.topic': to_verify['topic'],
            'hub.challenge': challenge
        }

        url = '?'.join([to_verify['callback'], urllib.urlencode(payload)])

        try:
            future = self.send(url, method='GET')
            response = future.result()
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
        """
        Verifies if the subscription request is valid and handles it
        appropriately.
        """

        if not self._env.get('REQUEST_METHOD', None) == 'POST':
            return self.respond(code=405, msg='Method Not Allowed.')

        query_st = self._env['wsgi.input'].read()
        args = urlparse.parse_qs(query_st)

        mode = args.get('hub.mode', [None])[0]
        callback = args.get('hub.callback', [None])[0]
        topic = args.get('hub.topic', [None])[0]
        verify = args.get('hub.verify', [None])
        lease = args.get('hub.lease_seconds', [2678400])[0]

        if not mode and not callback and not topic and not verify:
            return self.respond(code=400, msg="Bad request: Expected \
                'hub.mode', 'hub.callback', 'hub.topic', and 'hub.verify'")

        if not mode in ['subscribe', 'unsubscribe']:
            return self.respond(code=400, msg="Bad request: Unrecognized mode")

        verify = verify[0]
        if not verify in ['sync', 'async']:
            return self.respond(code=400,
                                msg="Bad request: \
                                Unsupported verification mode")

        to_verify = {'mode': mode,
                     'callback': callback,
                     'topic': topic,
                     'lease': lease}
        # async
        # FIXME: implement sync
        return self.subscribe(to_verify)


class HubRegister(Hub):
    """
    A HTML form for publishers to register at the hub. Expects a topic
    url and a valid xml payload. The xml payload is verified by javascript.
    Accepts only resourcesync payload.
    """

    def __init__(self, env, start_response):
        Hub.__init__(self)
        self._env = env
        self._start_response = start_response

    def handle(self):
        """
        Renders the form template.
        """

        if self._env.get('REQUEST_METHOD') not in ['GET', 'HEAD']:
            return self.respond(code=405, msg="Method not supported.")

        if self._env.get('REQUEST_METHOD') == 'HEAD':
            return self.respond()

        try:
            with open(os.path.join(os.path.dirname(__file__),
                                   "templates/register.html"), "r") \
                    as templ_file:
                template = templ_file.read()
                self._start_response("200 OK", [('Content-Type', 'text/html')])
                return [template]
        except IOError:
            return self.respond(code=500, msg="Unexpected server error")


class HubRegisterSuccess(Hub):
    """
    Displays the registration success page.
    """

    def __init__(self, env, start_response):
        Hub.__init__(self)
        self._env = env
        self._start_response = start_response

    def handle(self):
        """
        Renders the success template.
        """

        if self._env.get('REQUEST_METHOD') not in ['POST', 'HEAD']:
            return self.respond(code=405, msg="Method not supported.")

        if self._env.get('REQUEST_METHOD') == 'HEAD':
            return self.respond()

        topic_url = ""
        if self._env.get('REQUEST_METHOD') == 'POST' and \
                self._env.get('CONTENT_TYPE') == \
                "application/x-www-form-urlencoded":

            query_st = self._env['wsgi.input'].read()
            args = urlparse.parse_qs(query_st)
            topic_url = args.get('topic_url')[0]

        if not topic_url:
            return self.respond(code=400, msg="Bad Request")
        try:
            with open(os.path.join(os.path.dirname(__file__),
                                   "templates/register_success.html"), "r") \
                    as templ_file:
                template = templ_file.read()
                var = {'topic_url': topic_url,
                       'hub_url': self.config['my_url'] + "/publish"
                       }
                template = template.format(**var)
                self._start_response("200 OK", [('Content-Type', 'text/html')])
                return [template]
        except IOError as err:
            return self.respond(code=500,
                                msg="Unexpected server error: %s" % err)


def application(env, start_response):
    """
    WSGI entry point to the hub.
    """
    hub = Hub()
    urlparse.urlparse(hub.config['server_path'])

    req_path = env.get('PATH_INFO', "/")

    # replace server path
    if hub.config['server_path']:
        req_path = req_path.replace(hub.config['server_path'], "")

    if not req_path.startswith("/"):
        req_path = "/" + req_path

    if req_path == "/publish":
        publisher = HubPublisher(env, start_response)
        return publisher.handle()
    elif req_path == "/subscribe":
        subscriber = HubSubscriber(env, start_response)
        return subscriber.handle()
    elif req_path == "/register":
        hubregister = HubRegister(env, start_response)
        return hubregister.handle()
    elif req_path == "/registersuccess":
        hubregistersuccess = HubRegisterSuccess(env, start_response)
        return hubregistersuccess.handle()
    else:
        start_response("404 Not Found", [('Content-Type', 'text/html')])
        return ["Requested resource not found."]
