"""
A REST API for ResourceSync Publisher/Source.
"""

from resourcesync_push import ResourceSyncPuSH
import urlparse


class Publisher(ResourceSyncPuSH):
    """
    The ResourceSync Publisher.
    """

    def __init__(self, env, start_response):
        ResourceSyncPuSH.__init__(self)
        self._env = env
        self._start_response = start_response
        self.get_config()

    def make_link_header(self, hub_url=None, topic_url=None):
        """
        Constructs the resourcesync link header.
        """

        if not hub_url and not topic_url:
            return self.respond(code=400,
                                msg="hub and topic urls are not set \
                                in config file.")
        link_header = []
        link_header.extend(["<", topic_url, ">;rel=", "self", ","])
        link_header.extend([" <", hub_url, ">;rel=", "hub"])
        return "".join(link_header)

    def handle_topic(self):
        """
        Responds to head or get requests to the topic url with
        the link header according to the resourcesync spec.
        """
        if not self._env.get('REQUEST_METHOD', None) in ['HEAD', 'GET']:
            return self.respond(code=403, msg='Method Not Allowed.')

        link_header = self.make_link_header(topic_url=self.topic_url,
                                            hub_url=self.hub_url)
        headers = []
        headers.append(('Link', link_header))

        return self.respond(code=204, headers=headers)

    def handle(self):
        """
        Checks the request for necessary resourcesync parameters and
        publishes the notification to the hub.
        """

        if not self._env.get('REQUEST_METHOD', None) in ['HEAD', 'POST']:
            return self.respond(code=403, msg='Method Not Allowed.')

        if self._env.get('REQUEST_METHOD') == 'HEAD':
            return self.respond()

        content_type = self._env.get('CONTENT_TYPE', "").lower()
        if not content_type:
            return self.respond(code=400,
                                msg="Invalid Content-Type value in header.")

        # only supports resourcesync
        if not content_type == "application/xml":
            return self.respond(code=406,
                                msg="content-type header not recognised.")

        payload = None
        try:
            payload = self._env['wsgi.input'].read().strip()
        except Exception:
            #return self.respond(code=400,
            #                    msg="Payload of size > 0 expected.")
            pass

        if not self.hub_url or not self.topic_url or not payload:
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
    """
    The WSGI entry point. Also responds to topic urls specified in the config.
    """

    publisher = Publisher(env, start_response)

    urlparts = urlparse.urlparse(publisher.topic_url)
    topic_path = urlparts.path.replace(publisher.server_path, "")

    req_path = env.get('PATH_INFO', "/")

    # server path
    if publisher.server_path:
        req_path = req_path.replace(publisher.server_path, "")

    if not req_path.startswith("/"):
        req_path = "/" + req_path

    if not topic_path.startswith("/"):
        topic_path = "/" + topic_path

    if req_path == "/":
        return publisher.handle()
    elif req_path == topic_path:
        return publisher.handle_topic()
    else:
        start_response("404 Not Found", [('Content-Type', 'text/html')])
        return ["Requested resource not found."]
