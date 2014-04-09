from resync_push import ResyncPush
import urlparse


class Subscriber(ResyncPush):

    def __init__(self, env, start_response):
        ResyncPush.__init__(self)
        self._env = env
        self._start_response = start_response

    def process_subscription(self):
        payload = None
        try:
            payload = self._env['wsgi.input'].read()
        except:
            return self.respond(code=400,
                                msg="Payload of size > 0 expected.")
        args = urlparse.parse_qs(payload)
        data = {}
        hub_url = args.get('hub_url')[0]
        data['hub.topic'] = args.get('topic_url')[0]
        data['hub.callback'] = self.my_url
        data['hub.mode'] = 'subscribe'
        data['hub.verify'] = 'sync'

        headers = {'Content-Type': 'application/x-www-form-urlencoded'}

        self.send(hub_url, data=data, headers=headers)
        return self.respond(msg="Subscription request sent to the hub.")

    def process_resync_payload(self):
        # some basic tests for resync
        content_type = self._env.get('CONTENT_TYPE', None).lower()
        if not content_type:
            return self.respond(code=400,
                                msg="Invalid Content-Type value in header.")

        # only supports resourcesync
        if not content_type == "application/xml":
            # error
            return self.respond(code=403,
                                msg="content-type header not recognised.")

        payload = None
        try:
            payload = self._env['wsgi.input'].read()
        except:
            return self.respond(code=400,
                                msg="Payload of size > 0 expected.")

        print(payload)
        return self.respond()

    def handle(self):
        if not self._env.get('REQUEST_METHOD', None) in ['GET', 'POST']:
            return self.respond(code=403, msg='Method Not Allowed.')

        if self._env.get('REQUEST_METHOD') == 'GET' \
                and self._env.get('QUERY_STRING'):
            # must be subscription challenge...
            args = urlparse.parse_qs(self._env.get('QUERY_STRING'))
            challenge = args.get('hub.challenge')[0]
            if not challenge:
                return self.respond(code=404, msg="Resource not found.")
            return self.respond(code=200, msg=challenge)
        elif self._env.get('CONTENT_TYPE').lower() == \
                'application/x-www-form-urlencoded':
            return self.process_subscription()
        elif self._env.get('CONTENT_TYPE').lower() == 'application/xml':
            return self.process_resync_payload()
        return self.respond(code=404, msg='Resource not found.')


def application(env, start_response):
    req_path = env.get('PATH_INFO', "/")

    if req_path == "/":
        s = Subscriber(env, start_response)
        return s.handle()
    else:
        start_response("404 Not Found", [('Content-Type', 'text/html')])
        return ["Requested resource not found."]
