import requests
import datetime
import logging
import config

def parse_canonical(canonical, full_url, url, iterate_list_of_urls, discovered_urls):
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
	check_if_indexed = requests.post("https://es-indieweb-search.jamesg.blog/check?url={}".format(full_url), headers={"Authorization": "Bearer {}".format(config.ELASTICSEARCH_API_TOKEN)}).json()

	if len(check_if_indexed) > 0:
		# remove url from index if it no longer works
		data = {
			"id": check_if_indexed["_id"],
		}
		requests.post("https://es-indieweb-search.jamesg.blog/remove-from-index", headers={"Authorization": "Bearer {}".format(config.ELASTICSEARCH_API_TOKEN)}, json=data)
		logging.info("removed {} from index as it is no longer valid".format(full_url))

def save_feed(site, full_url, feed_url, feed_type, feeds, feed_urls):
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