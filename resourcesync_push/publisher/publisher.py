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

    def handle_topic(self):
        """
        Responds to head or get requests to the topic url with
        the link header according to the resourcesync spec.
        """
        if not self._env.get('REQUEST_METHOD', None) in ['HEAD', 'GET']:
            return self.respond(code=403, msg='Method Not Allowed.')

        link_header = self.make_link_header(topic_url=self.config['topic_url'],
                                            hub_url=self.config['hub_url'])
        headers = []
        headers.append(('Link', link_header))

        return self.respond(code=204, headers=headers)

    def create_change_notification(self, lastmod=None, loc=None, md=None):
        """
        Creates the change notification payload.
        """

        notification_template = """
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
 xmlns:rs="http://www.openarchives.org/rs/terms/">
{url}
</urlset>
        """

        if not md and not lastmod and not loc:
            return None

        notificaiton = []
        notificaiton.append("<url>")
        notificaiton.extend(["<loc>", loc, "</loc>"])
        notificaiton.extend(["<lastmod>", lastmod, "</lastmod>"])
        notificaiton.extend(['<rs:md change="', md['change'], '" '])
        if md['change'] != "deleted":
            notificaiton.extend(['hash="md5:', md['hash'], '" ',
                                 'length="', md['length'], '" ',
                                 'type="', md['type'], '" '])
        else:
            md['hash'] = None
        notificaiton.append(" />")
        notificaiton.append("</url>")

        return notification_template.format(url="".join(notificaiton))

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
        if content_type == "application/xml":
            return self.process_resourcesync_payload()
            """
            elif content_type == "application/x-www-form-urlencoded":
                query_st = self._env['wsgi.input'].read().strip()
                query = urlparse.parse_qs(query_st)

                topic_url = query.get('topic_url', [None])[0]
                change = query.get("change", [None])[0]
                resource_url = query.get("resource_url", [None])[0]

                link_header = self.make_link_header(
                topic_url=topic_url,
                hub_url=self.config['hub_url'])
                payload = self.create_change_notification()
                self.process_resourcesync_payload()
            """
        else:
            return self.respond(code=406,
                                msg="content-type header not recognised.")

        return

    def process_resourcesync_payload(self):
        """
        Sends the resourcesync payload to the hub. The topic and hub url must
        already be configured in the config file.
        """

        payload = self._env['wsgi.input'].read().strip()

        if not self.config['hub_url'] or\
                not self.config['topic_url'] or\
                not payload:
            return self.respond(code=400,
                                msg="hub url, topic url and payload \
                                is required.")

        link_header = self.make_link_header(topic_url=self.config['topic_url'],
                                            hub_url=self.config['hub_url'])

        self.log_msg['payload'] = payload
        self.log_msg['link_header'] = link_header
        self.log_msg['msg'].append("Payload size: %s bytes." %
                                   str(len(payload)))

        headers = {}
        headers['Content-Type'] = "application/xml"
        headers['Link'] = link_header
        headers['Content-Length'] = str(len(payload))

        self.send(url=self.config['hub_url'],
                  headers=headers,
                  data=payload)
        self.log()
        return self.respond()


def application(env, start_response):
    """
    The WSGI entry point. Also responds to topic urls specified in the config.
    """

    publisher = Publisher(env, start_response)

    urlparts = urlparse.urlparse(publisher.config['topic_url'])
    topic_path = urlparts.path.replace(publisher.config['server_path'], "")

    req_path = env.get('PATH_INFO', "/")

    # server path
    if publisher.config['server_path']:
        req_path = req_path.replace(publisher.config['server_path'], "")

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
