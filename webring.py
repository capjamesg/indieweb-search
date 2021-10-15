import requests
from bs4 import BeautifulSoup

r = requests.get("https://xn--sr8hvo.ws/")

# get all links on page

soup = BeautifulSoup(r.text, "html.parser")

links = soup.find_all("a")

links = 