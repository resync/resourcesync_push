"""
A ResourceSync Subscriber.
"""

from resourcesync_push import ResourceSyncPuSH
import urlparse


class Subscriber(ResourceSyncPuSH):
    """
    Handles subscription requests and verification. Will receive
    ResourceSync payload. Should be extended to perform any meaningful
    tasks with the payload.
    """

    def __init__(self, env, start_response):
        ResourceSyncPuSH.__init__(self)
        self._env = env
        self._start_response = start_response
        self.get_config()

    def process_subscription(self):
        """
        Sends subscription request for a topic to the
        hub.
        """

        payload = self._env['wsgi.input'].read()
        if not payload:
            return self.respond(code=400,
                                msg="Payload of size > 0 expected.")
        args = urlparse.parse_qs(payload)
        data = {}
        hub_url = args.get('hub_url', [None])[0]
        data['hub.topic'] = args.get('topic_url', [None])[0]
        data['hub.callback'] = self.config['my_url']
        data['hub.mode'] = 'subscribe'
        data['hub.verify'] = 'sync'

        headers = {'Content-Type': 'application/x-www-form-urlencoded'}

        self.send(hub_url, data=data, headers=headers)
        return self.respond(msg="Subscription request sent to the hub.")

    def process_resourcesync_payload(self):
        """
        Receives and performs basic verification of the
        resourcesync payload.
        NOTE: The method should be extended to do
        something useful with the payload.
        """

        # some basic tests for resourcesync
        content_type = self._env.get('CONTENT_TYPE', None).lower()
        if not content_type:
            return self.respond(code=400,
                                msg="Invalid Content-Type value in header.")

        # only supports resourcesync
        if not content_type == "application/xml":
            # error
            return self.respond(code=403,
                                msg="content-type header not recognised.")

        payload = self._env['wsgi.input'].read()
        if not payload:
            return self.respond(code=400,
                                msg="Payload of size > 0 expected.")

        self.log_msg['payload'] = payload
        self.log_msg['link_header'] = self._env.get('HTTP_LINK', None)
        self.log()

        return self.respond()

    def process_subscription_challenge(self):
        """
        Responds to the subscription challenge from the hub.
        """

        args = urlparse.parse_qs(self._env.get('QUERY_STRING', None))
        challenge = args.get('hub.challenge', [None])[0]
        if not challenge:
            return self.respond(code=400, msg="Bad Request.")
        return self.respond(code=200, msg=challenge)

    def handle(self):
        """
        Checks the request to see if it's for subscription or
        resourcesync payload and handles appropriately.
        """
        if not self._env.get('REQUEST_METHOD', None) in \
                ['GET', 'POST', 'HEAD']:
            return self.respond(code=405, msg='Method Not Allowed.')

        if self._env.get('REQUEST_METHOD') == 'HEAD':
            return self.respond()

        if self._env.get('REQUEST_METHOD') == 'GET' \
                and self._env.get('QUERY_STRING'):
            # must be subscription challenge...
            return self.process_subscription_challenge()
        elif self._env.get('CONTENT_TYPE', "").lower() == \
                'application/x-www-form-urlencoded':
            return self.process_subscription()
        elif self._env.get('CONTENT_TYPE', "").lower() == 'application/xml':
            return self.process_resourcesync_payload()
        return self.respond(code=400, msg='Bad Request.')


def application(env, start_response):
    """
    WSGI entry point.
    """

    subscriber = Subscriber(env, start_response)
    urlparse.urlparse(subscriber.config['server_path'])

    req_path = env.get('PATH_INFO', "/")

    # replace server path
    if subscriber.config['server_path']:
        req_path = req_path.replace(subscriber.config['server_path'], "")

    if not req_path.startswith("/"):
        req_path = "/" + req_path

    if req_path == "/":
        return subscriber.handle()
    else:
        start_response("404 Not Found", [('Content-Type', 'text/html')])
        return ["Requested resource not found."]
