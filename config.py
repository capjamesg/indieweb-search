import os

HEADERS = {
	"User-agent": "indieweb-search"
}

# excluded_from_in_page_crawl = ["https://{}".format(SITE_URL), "http://{}".format(SITE_URL)]

ROOT_DIRECTORY = os.path.dirname(os.path.abspath("__init__.py"))

SECRET_KEY = os.urandom(24)