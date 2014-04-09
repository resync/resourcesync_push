from requests_futures.sessions import FuturesSession
from requests.utils import parse_header_links
from requests.adapters import HTTPAdapter
import ConfigParser
import os


class ResyncPush():

    def __init__(self, classname=None):

        if not classname:
            classname = self.__class__.__name__.lower()

        # FIXME: max workers should be configurable
        self.session = FuturesSession(max_workers=10)
        a = HTTPAdapter(max_retries=3)
        self.session.mount("http://", a)

        # loading values from configuration file
        conf = ConfigParser.ConfigParser()
        conf.read(os.path.join(os.path.dirname(__file__),
                               "../conf/resync.cnf"))

        if classname == "hub":
            self.get_hub_config(conf)
        elif classname == "publisher":
            self.get_publisher_config(conf)
        elif classname == "subscriber":
            self.my_url = ""
            try:
                self.my_url = conf.get("subscriber", "url")
            except:
                print("The url value for subscriber is required \
                      in the config file.")
                raise

        self.log_mode = ""
        try:
            self.log_mode = conf.get("general", "log_mode")
        except:
            pass

    def get_hub_config(self, conf):
        self.mimetypes = []
        try:
            self.mimetypes = conf.get("hub", "mimetypes")
        except:
            # reourcesync hub by default
            self.mimetypes = "application/xml"

        self.trusted_publishers = []
        try:
            self.trusted_publishers = conf.get("hub", "trusted_publishers")
        except:
            # will allow any publisher
            self.trusted_publishers = []

        self.trusted_topics = []
        try:
            self.trusted_topics = conf.get("hub", "trusted_topics")
        except:
            # will accept any topic
            self.trusted_topics = []

        self.my_url = ""
        try:
            self.my_url = conf.get("hub", "url")
        except:
            print("The url value for hub is required in the config file.")
            raise

        self.subscribers_file = os.path.join(os.path.dirname(__file__),
                                             "../db/subscriptions.pk")
        try:
            self.subscribers_file = conf.get("hub", "subscribers_file")
        except:
            pass

        if not os.path.isfile(self.subscribers_file):
            open(self.subscribers_file, 'a').close()

    def get_publisher_config(self, conf):
        self.my_url = ""
        try:
            self.my_url = conf.get("publisher", "url")
        except:
            print("The url value for publisher is required \
                  in the config file.")
            raise

        self.hub_url = ""
        try:
            self.hub_url = conf.get("publisher", "hub_url")
        except:
            print("The hub_url value for publisher is required \
                  in the config file.")
            raise

        self.topic_url = ""
        try:
            self.topic_url = conf.get("publisher", "topic_url")
        except:
            print("The topic_url value for publisher is required \
                  in the config file.")
            raise

    def send(self, url, method='POST',
             data=None,
             callback=None,
             headers=None):

        if method == 'POST':
            return self.session.post(url,
                                     data=data,
                                     background_callback=callback,
                                     headers=headers)
        elif method == 'GET':
            return self.session.get(url,
                                    headers=headers)
        else:
            return

    def respond(self, code=200, msg="OK"):
        print("HTTP %s: %s" % (code, msg))
        self._start_response(str(code), [("Content-Type", "text/html")])
        return [msg]

    def process_response(self, future_session, response):
        if not response.status_code == "200":
            print("HTTP Error: %s" % (response.status_code))
            return
        print(response.status_code)

    def get_topic_hub_url(self, link_header):
        links = parse_header_links(link_header)
        topic = ""
        hub_url = ""
        for l in links:
            if l.get('rel') == 'self':
                topic = l.get('url')
            elif l.get('rel') == 'hub':
                hub_url = l.get('url')
        return (topic, hub_url)
