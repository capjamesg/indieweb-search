import requests
import datetime
import logging
import config
import indieweb_utils

def parse_canonical(canonical, full_url, url, iterate_list_of_urls, discovered_urls):
	"""
		Check if a URL is canonical.

		:param canonical: The canonical URL
		:param full_url: The full URL of a resource
		:param url: The URL
		:param iterate_list_of_urls: The list of URLs to iterate through
		:param discovered_urls: The list of URLs discovered

		:return: The canonical URL
	"""
	canonical_domain = canonical.split("/")[2]

	if canonical_domain.lower().replace("www.", "") != full_url.split("/")[2].lower().replace("www.", ""):
		logging.info("{} has a canonical url of {}, not adding to queue because url points to a different domain".format(full_url, canonical))

		return True

	if canonical and canonical != full_url.lower().strip("/").replace("http://", "https://").split("?")[0]:
		if discovered_urls.get(full_url) and discovered_urls.get(full_url).startswith("CANONICAL"):
			logging.info("{} has a canonical url of {}, not adding to index because the page was already identified as canonical".format(full_url, canonical))
		else:
			canonical_url = url

			iterate_list_of_urls.append(canonical_url)

			discovered_urls[canonical_url] = "CANONICAL {}".format(full_url)

			logging.info("{} has a canonical url of {}, skipping and added canonical URL to queue".format(full_url, canonical_url))

			return True

	return False

def check_remove_url(full_url):
	"""
		Check if a URL should be removed.

		:param full_url: The full URL of a resource to check
	"""
	check_if_indexed = requests.post("https://es-indieweb-search.jamesg.blog/check?url={}".format(full_url), headers={"Authorization": "Bearer {}".format(config.ELASTICSEARCH_API_TOKEN)}).json()

	if len(check_if_indexed) > 0:
		# remove url from index if it no longer works
		data = {
			"id": check_if_indexed["_id"],
		}
		requests.post("https://es-indieweb-search.jamesg.blog/remove-from-index", headers={"Authorization": "Bearer {}".format(config.ELASTICSEARCH_API_TOKEN)}, json=data)
		logging.info("removed {} from index as it is no longer valid".format(full_url))

def save_feed(site, full_url, feed_url, feed_type, feeds, feed_urls):
	"""
		Add a feed to the list of feeds found on a website.

		:param site: The site being crawled
		:param full_url: The full URL of the page on which the feed was found
		:param feed_url: The feed URL
		:param feed_type: The feed type
		:param feeds: The list of feeds found on the site
		:param feed_urls: The list of feed URLs found on the site

		:return: The list of feeds found on the site
	"""
	supported_protocols = ["http", "https"]

	if feed_url != None and ("://" in feed_url and feed_url.split("://")[0] not in supported_protocols) or (":" in feed_url \
		and (not feed_url.startswith("/") and not feed_url.startswith("//") and not feed_url.startswith("#") \
		and not feed_url.split(":")[0] in supported_protocols)):
		# url is wrong protocol, continue

		logging.info("Unsupported protocol for discovered feed: " + feed_url + ", not adding to fef queue")
		return feeds, feed_urls

	feeds.append({"website_url": site, "page_url": full_url, "feed_url": feed_url, "mime_type": feed_type, "etag": "NOETAG", "discovered": datetime.datetime.now().strftime("%Y-%m-%d")})
	feed_urls.append(feed_url.strip("/"))
	
	logging.info("found feed {}, will save".format(feed_url))

	return feeds, feed_urls

def find_feeds(page_desc_soup, full_url, site):
	"""
		Find the feeds provided in HTTP headers and on a HTML web page.

		:param page_desc_soup: The BeautifulSoup object of the HTML page
		:param full_url: The full URL of the page on which the feed was found
		:param site: The site being crawled
	"""
	if page_desc_soup.find_all("link", {"rel": "alternate"}):
		for feed_item in page_desc_soup.find_all("link", {"rel": "alternate"}):
			if feed_item and feed_item["href"].startswith("/"):
				# get site domain
				domain = full_url.split("/")[2]
				feed_url = indieweb_utils.canonicalize_url(full_url.split("/")[0] + "//" + domain + feed_item["href"])

				if feed_url and feed_url not in feed_urls:
					feeds, feed_urls = save_feed(site, full_url, feed_url, feed_item.get("type"), feeds, feed_urls)
					
			elif feed_item and feed_item["href"].startswith("http"):
				if feed_item["href"] not in feed_urls and feed_item["href"].split("/")[2] == full_url.split("/")[2]:
					feeds, feed_urls = save_feed(site, full_url, feed_url, feed_item.get("type"), feeds, feed_urls)
					
				elif feed_item["href"] not in feed_urls and feed_item["href"].split("/")[2] != full_url.split("/")[2]:
					print("found feed {}, but it points to a different domain, not saving".format(feed_item["href"]))
					logging.info("found feed {}, but it points to a different domain, not saving".format(feed_item["href"]))
			else:
				feeds, feed_urls = save_feed(site, full_url, full_url.strip("/") + "/" + feed_url, feed_item.get("type"), feeds, feed_urls)

	# check if page has h-feed class on it
	# if a h-feed class is present, mark page as feed

	if page_desc_soup.select(".h-feed") and len(feeds) < 25:
		feeds.append({"website_url": site, "page_url": full_url, "feed_url": full_url, "mime_type": "h-feed", "etag": "NOETAG", "discovered": datetime.datetime.now().strftime("%Y-%m-%d")})
		feed_urls.append(full_url.strip("/"))

		logging.info("{} is a h-feed, will save to feeds.json".format(full_url))

	# check for websub hub

	if page_desc_soup.find("link", {"rel": "hub"}) and len(feeds) < 25:
		websub_hub = page_desc_soup.find("link", {"rel": "hub"})["href"]

		websub_hub = websub_hub.strip().strip("<").strip(">")

		feeds.append({"website_url": site, "page_url": full_url, "feed_url": websub_hub, "mime_type": "websub", "etag": "NOETAG", "discovered": datetime.datetime.now().strftime("%Y-%m-%d")})
		
		feed_urls.append(full_url.strip("/"))

		logging.info("{} is a websub hub, will save to feeds.json".format(full_url))

	return feeds, feed_urls