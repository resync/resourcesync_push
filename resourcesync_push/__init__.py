"""
The base class for the publisher, hub and resource. Contains
methods for reading config files, making http requests, error handling,
etc.
"""

from requests_futures.sessions import FuturesSession
from requests.utils import parse_header_links
from requests.adapters import HTTPAdapter
import ConfigParser
from ConfigParser import NoOptionError, NoSectionError
import os
import json


HTTP_STATUS_CODE = {
    200: "OK",
    204: "No Content",
    302: "Found",
    400: "Bad Request",
    403: "Forbidden",
    404: "Not Found",
    405: "Method Not Allowed",
    406: "Not Acceptable",
    409: "Conflict",
    500: "Unexpected server error",
}


class ResourceSyncPuSH(object):
    """
    The base class for the publisher, hub and resource. Contains
    methods for reading config files, making http requests, error handling,
    etc.
    """

    def __init__(self):
        """
        Inititalizes the Futures-Requests session with the
        max number of workers and retires.
        """

        # max workers and retries should be configurable?
        self.session = FuturesSession(max_workers=10)
        adapter = HTTPAdapter(max_retries=3)
        self.session.mount("http://", adapter)
        self._start_response = None

        # config parameters
        self.config = {}
        self.config['log_mode'] = ""
        self.config['mimetypes'] = []
        self.config['trusted_publishers'] = []
        self.config['trusted_topics'] = []
        self.config['my_url'] = ""
        self.config['hub_url'] = ""
        self.config['topic_url'] = ""
        self.config['subscribers_file'] = ""
        self.config['server_path'] = ""

        # logging messages
        self.log_msg = {}
        self.log_msg['payload'] = ""
        self.log_msg['msg'] = []
        self.log_msg['link_header'] = ""
        self.log_msg['module'] = ""

    def get_config(self, classname=None):
        """
        Finds and reads the config file. Reads the appropriate config values
        for the classname provided. For eg: if the classname is hub, it will
        read from the [hub] section in the config file.
        """

        if not classname:
            classname = self.__class__.__name__.lower()

        self.log_msg['module'] = classname

        # NOTE: more paths can be added to look for the config files.
        # order of files matter, the config in the first file
        # will be overwritten by the values in the next file.
        cnf_file = []
        cnf_file.extend([
            os.path.join(os.path.dirname(__file__),
                         "../conf/resourcesync_push.ini"),
            "/etc/resourcesync_push.ini",
            "/etc/resourcesync_push/resourcesync_push.ini",
        ])

        # loading values from configuration file
        conf = ConfigParser.ConfigParser()
        conf.read(cnf_file)
        if not conf:
            raise IOError("Unable to read config file")

        if classname == "hub":
            self.get_hub_config(conf)
        elif classname == "publisher":
            self.get_publisher_config(conf)
        elif classname == "subscriber":
            try:
                self.config['my_url'] = conf.get("subscriber", "url")
            except (NoSectionError, NoOptionError):
                print("The url value for subscriber is required \
                      in the config file.")
                raise

        self.get_demo_config(conf)

    def get_demo_config(self, conf):
        """
        Reads the [demo_hub] section from the config file if the
        log mode is set to 'demo'.
        """
        try:
            self.config['log_mode'] = conf.get("general", "log_mode")
        except (NoSectionError, NoOptionError):
            pass

        if not self.config['log_mode'] == "demo":
            return

        try:
            self.config['demo_hub_url'] = conf.get("demo_mode", "hub_url")
        except (NoSectionError, NoOptionError):
            print("Demo log mode requires a hub_url in the \
                  [demo_mode] section")
            raise

        try:
            self.config['demo_topic_url'] = conf.get("demo_mode", "topic_url")
        except (NoSectionError, NoOptionError):
            print("Demo log mode requires a topic_url in the \
                  [demo_mode] section")
            raise
        return

    def get_hub_config(self, conf):
        """
        Reads the [hub] section from the config file.
        """

        try:
            self.config['mimetypes'] = conf.get("hub", "mimetypes")
        except (NoSectionError, NoOptionError):
            # reourcesync hub by default
            self.config['mimetypes'] = "application/xml"

        try:
            self.config['trusted_publishers'] = conf.get("hub",
                                                         "trusted_publishers")
        except (NoSectionError, NoOptionError):
            # will allow any publisher
            self.config['trusted_publishers'] = []

        try:
            self.config['trusted_topics'] = conf.get("hub", "trusted_topics")
        except (NoSectionError, NoOptionError):
            # will accept any topic
            self.config['trusted_topics'] = []

        try:
            self.config['my_url'] = conf.get("hub", "url")
        except (NoSectionError, NoOptionError):
            print("The url value for hub is required in the config file.")
            raise

        self.config['subscribers_file'] = os.path.join(
            os.path.dirname(__file__),
            "../db/subscriptions.pk"
        )
        try:
            self.config['subscribers_file'] = conf.get("hub",
                                                       "subscribers_file")
        except (NoSectionError, NoOptionError):
            pass

        if not os.path.isfile(self.config['subscribers_file']):
            open(self.config['subscribers_file'], 'a').close()

        return

    def get_publisher_config(self, conf):
        """
        Reads the [publisher] section in the config file.
        """

        try:
            self.config['my_url'] = conf.get("publisher", "url")
        except (NoSectionError, NoOptionError):
            print("The url value for publisher is required \
                  in the config file.")
            raise

        try:
            self.config['server_path'] = conf.get("publisher", "server_path")
        except (NoSectionError, NoOptionError):
            pass

        try:
            self.config['hub_url'] = conf.get("publisher", "hub_url")
        except (NoSectionError, NoOptionError):
            print("The hub_url value for publisher is required \
                  in the config file.")
            raise

        try:
            self.config['topic_url'] = conf.get("publisher", "topic_url")
        except (NoSectionError, NoOptionError):
            print("The topic_url value for publisher is required \
                  in the config file.")
            raise

    def send(self, url, method='POST',
             data=None,
             callback=None,
             headers=None):
        """
        Performs http post and get requests. Uses futures-requests
        to make (threaded) async requests.
        """

        if method == 'POST':
            return self.session.post(url,
                                     data=data,
                                     background_callback=callback,
                                     headers=headers)
        elif method == 'GET':
            return self.session.get(url,
                                    headers=headers)
        elif method == 'HEAD':
            return self.session.head(url,
                                     headers=headers)
        else:
            return

    def respond(self, code=200, msg="OK", headers=None):
        """
        Sends the appropriate http status code with an
        error message.
        """

        print("HTTP %s: %s" % (code, msg))

        if not headers:
            headers = []
        if not str(code) == "204":
            headers.append(("Content-Type", "text/html"))

        code = str(code) + " " + HTTP_STATUS_CODE[code]

        self._start_response(code, headers)
        return [msg]

    @staticmethod
    def get_topic_hub_url(link_header):
        """
        Uses the parse_header_links method in requests to parse link
        headers and return the topic and hub urls.
        """

        links = parse_header_links(link_header)
        topic = ""
        hub_url = ""
        for link in links:
            if link.get('rel') == 'self':
                topic = link.get('url')
            elif link.get('rel') == 'hub':
                hub_url = link.get('url')
        return (topic, hub_url)

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

    def log(self):
        """
        Log handler. Will send the log info as json to the
        demo hub if log_mode value is set to demo in the config file.
        """
        if self.config['log_mode'] == 'demo':
            headers = {}
            headers['Link'] = self.make_link_header(
                hub_url=self.config['demo_hub_url'],
                topic_url=self.config['demo_topic_url']
            )
            self.send(self.config['demo_hub_url'],
                      data=json.dumps(self.log_msg),
                      headers=headers)
        else:
            print(self.log_msg)
