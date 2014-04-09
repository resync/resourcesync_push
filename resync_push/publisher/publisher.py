from resync_push import ResyncPush


class Publisher(ResyncPush):

    def __init__(self, env, start_response):
        ResyncPush.__init__(self)
        self._env = env
        self._start_response = start_response

    def make_link_header(self, hub_url=None, topic_url=None):
        if not hub_url and not topic_url:
            return self.respond(code=400,
                                msg="hub and topic urls are not set \
                                in config file.")
        link_header = []
        link_header.extend(["<", topic_url, ">; rel=", "self", ","])
        link_header.extend(["<", hub_url, ">; rel=", "hub", ","])
        return "".join(link_header)

    def handle(self):
        if not self._env.get('REQUEST_METHOD', None) == 'POST':
            return self.respond(code=403, msg='Method Not Allowed.')

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

        if not self.hub_url and not self.topic_url and not payload:
            return self.respond(code=400,
                                msg="hub url, topic url and payload \
                                is required.")

        link_header = self.make_link_header(topic_url=self.topic_url,
                                            hub_url=self.hub_url)

        headers = {}
        headers['Content-Type'] = content_type
        headers['Link'] = link_header
        headers['Content-Length'] = str(len(payload))

        self.send(url=self.hub_url,
                  headers=headers,
                  data=payload)
        return self.respond()


def application(env, start_response):
    req_path = env.get('PATH_INFO', "/")

    if req_path == "/":
        p = Publisher(env, start_response)
        return p.handle()
    else:
        start_response("404 Not Found", [('Content-Type', 'text/html')])
        return ["Requested resource not found."]
