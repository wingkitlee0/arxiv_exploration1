import time
# python 3
import urllib.error
from urllib.request import urlopen
import datetime
#from itertools import ifilter
from collections import Counter, defaultdict
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup
import matplotlib.pylab as plt
import pandas as pd
import numpy as np

pd.set_option('mode.chained_assignment','warn')

OAI = "{http://www.openarchives.org/OAI/2.0/}"
ARXIV = "{http://arxiv.org/OAI/arXiv/}"

class ArxivAnalysis:
    
    def __init__(self):
        self.category_default = "physics:astro-ph"
        self.base_url = "http://export.arxiv.org/oai2?verb=ListRecords"
        

    def harvest(self, arxiv=None, from_date="2016-08-01", until_date="2016-08-31"):
        """
        input: arxiv is the "set" defined in http://export.arxiv.org/oai2?verb=ListSets
        """

        if arxiv is None:
            arxiv = self.category_default

        df = pd.DataFrame(columns=("title", "abstract", "categories", "created", "id", "doi"))
        url = (self.base_url +
            "&from=%s" % from_date +
            "&until=%s" % until_date + 
            "&metadataPrefix=arXiv&set=%s"%arxiv)
        
        while True:
            print("fetching", url)
            try:
                response = urlopen(url)
                
            except urllib.error.HTTPError as e:
                if e.code == 503:
                    to = int(e.hdrs.get("retry-after", 30))
                    print("Got 503. Retrying after {0:d} seconds.".format(to))

                    time.sleep(to)
                    continue
                    
                else:
                    raise
                
            xml = response.read()

            root = ET.fromstring(xml)

            for record in root.find(OAI+'ListRecords').findall(OAI+"record"):
                arxiv_id = record.find(OAI+'header').find(OAI+'identifier')
                meta = record.find(OAI+'metadata')
                info = meta.find(ARXIV+"arXiv")
                created = info.find(ARXIV+"created").text
                created = datetime.datetime.strptime(created, "%Y-%m-%d")
                categories = info.find(ARXIV+"categories").text

                # if there is more than one DOI use the first one
                # often the second one (if it exists at all) refers
                # to an eratum or similar
                doi = info.find(ARXIV+"doi")
                if doi is not None:
                    doi = doi.text.split()[0]
                    
                contents = {'title': info.find(ARXIV+"title").text,
                            'id': info.find(ARXIV+"id").text,#arxiv_id.text[4:],
                            'abstract': info.find(ARXIV+"abstract").text.strip(),
                            'created': created,
                            'categories': categories.split(),
                            'doi': doi,
                            }

                df = df.append(contents, ignore_index=True)

            # The list of articles returned by the API comes in chunks of
            # 1000 articles. The presence of a resumptionToken tells us that
            # there is more to be fetched.
            token = root.find(OAI+'ListRecords').find(OAI+"resumptionToken")
            if token is None or token.text is None:
                break

            else:
                url = self.base_url + "&resumptionToken=%s"%(token.text)
                
        return df
        

