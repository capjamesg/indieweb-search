link = {"href": "https://j"}

supported_protocols = ["http", "https"]

if ("://" in link.get("href") and link.get("href").split("://")[0] not in supported_protocols) or (":" in link.get("href") \
    and (not link.get("href").startswith("/") and not link.get("href").startswith("//") and not link.get("href").startswith("#") \
    and not link.get("href").split(":")[0] in supported_protocols)):
    # url is wrong protocol, continue
    print("Unsupported protocol for discovered url: " + link.get("href") + ", not adding to index queue")

import requests
import hashlib

r = requests.get("https://jamesg.blog")

from bs4 import BeautifulSoup

soup = BeautifulSoup(r.text, "lxml")

# get body of page
body = soup.find("body")

# get hash of web page
hash = hashlib.sha256(str(body).encode('utf-8')).hexdigest()

print(hash)

import re

domain = "https://jamesg.blog/test/test/test/test/test/"

# if re matches    ^.*?(/.+?/).*?\1.*$|^.*?/(.+?/)\2.*$
# https://support.archive-it.org/hc/en-us/articles/208332943-Identify-and-avoid-crawler-traps-
check = re.compile(r"^.*?(/.+?/).*?\1.*$|^.*?/(.+?/)\2.*$")

if check.match(domain):
    print("match")
else:
    print("no match")