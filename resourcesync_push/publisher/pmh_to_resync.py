"""
Reads a PMH feed periodically and converts the PMH records
in ResouceSync format.
"""

from resync_push import ResyncPush
import xml.etree.ElementTree as ET
import time
import StringIO


# the xml namespaces used in pmh
XMLNS = {
    "ns": "http://www.openarchives.org/OAI/2.0/",
    "xsi": "http://www.w3.org/2001/XMLSchema-instance",
    "dc": "http://purl.org/dc/elements/1.1/",
    "oai_dc": "http://www.openarchives.org/OAI/2.0/oai_dc/",
}

# the pmh endpoint for the verb ListRecords
PMH_ENDPOINT = "http://core.kmi.open.ac.uk/faithfuloai?verb=ListRecords&metadataPrefix=oai_dc&from=%s"


class PMHToResync(ResyncPush):

    def __init__(self):
        ResyncPush.__init__(self)
        self.time_format_str = '%Y-%m-%dT%H:%M:%SZ'  # ISO-8601

    def format_time(self, t=None):
        """
        Formats the given time in to the time format defined by the class.
        Defaults to current time.
        """
        if not t:
            t = time.time()
        return time.strftime(self.time_format_str, time.gmtime(t))

    def parse_pmh(self, data):
        """
        Parses PMH data and returns a dict of records.
        dict[<identifier>] = {dateMod:, dc_identifier:}
        """

        data = data.strip()
        tree = None
        try:
            tree = ET.parse(StringIO.StringIO(data))
        except:
            raise

        root = tree.getroot()
        return root


    def handle(self):
        """
        The entry point. Retrieves the pmh doc and sends it to parsing.
        """

        url = PMH_ENDPOINT % self.format_time(time.time() - 3600)
        print(url)
        future = self.send(url, method='GET')
        while future.running():
            pass
        if future.done():
            res = future.result()
            return self.parse_pmh(res.content)


if __name__ == '__main__':
    ptore = PMHToResync()
    ptore.handle()
