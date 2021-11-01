from bs4 import BeautifulSoup
import requests
import datetime
import logging
import config
import crawler.page_info
import crawler.add_to_database as add_to_database
import crawler.discovery as page_link_discovery
import hashlib

yesterday = datetime.datetime.today() - datetime.timedelta(days=1)

def check_remove_url(full_url):
	check_if_indexed = requests.post("https://es-indieweb-search.jamesg.blog/check?url={}".format(full_url), headers={"Authorization": "Bearer {}".format(config.ELASTICSEARCH_API_TOKEN)}).json()

	if len(check_if_indexed) > 0:
		# remove url from index if it no longer works
		data = {
			"id": check_if_indexed["_id"],
		}
		requests.post("https://es-indieweb-search.jamesg.blog/remove-from-index", headers={"Authorization": "Bearer {}".format(config.ELASTICSEARCH_API_TOKEN)}, json=data)
		print("removed {} from index as it is no longer valid".format(full_url))
		logging.info("removed {} from index as it is no longer valid".format(full_url))

def save_feed(site, full_url, feed_url, feed_type, feeds, feed_urls):
	supported_protocols = ["http", "https"]

	if feed_url != None and ("://" in feed_url and feed_url.split("://")[0] not in supported_protocols) or (":" in feed_url \
		and (not feed_url.startswith("/") and not feed_url.startswith("//") and not feed_url.startswith("#") \
		and not feed_url.split(":")[0] in supported_protocols)):
		# url is wrong protocol, continue
		print("Unsupported protocol for discovered feed: " + feed_url + ", not adding to feed queue")
		logging.info("Unsupported protocol for discovered feed: " + feed_url + ", not adding to fef queue")
		return feeds, feed_urls

	feeds.append({"website_url": site, "page_url": full_url, "feed_url": feed_url, "mime_type": feed_type, "etag": "NOETAG", "discovered": datetime.datetime.now().strftime("%Y-%m-%d")})
	feed_urls.append(feed_url.strip("/"))
	# print("found feed {}, will save".format(feed_url))
	logging.info("found feed {}, will save".format(feed_url))

	return feeds, feed_urls

def crawl_urls(final_urls, namespaces_to_ignore, pages_indexed, all_links, external_links, discovered_urls, iterate_list_of_urls, site_url, 
	crawl_budget, url, feeds, feed_urls, site, session, web_page_hashes, average_crawl_speed, homepage_meta_description, 
	link_discovery=True, h_card=[], crawl_depth=0):
	"""
		Crawls URLs in list, adds URLs to index, and returns updated list
	"""
	count = 0

	print(url)

	feeds = []

	# make sure urls with // are processed correctly
	# example: https://www.test.com//text.html should become https://www.test.com/text.html
	if "//" in url.replace("://", ""):
		if url.startswith("http://"):
			protocol = "http://"
		elif url.startswith("https://"):
			protocol = "https://"

		url = url.replace("http://", "").replace("https://", "").replace("//", "/")

		url = protocol + url

	full_url = url

	if len(full_url) > 125:
		print("{} url too long, skipping".format(full_url))
		logging.info("{} url too long, skipping".format(full_url))
		return url, {}, False, feeds, None, crawl_depth, average_crawl_speed

	if "javascript:" in full_url:
		print("{} marked as noindex because it is a javascript resource".format(full_url))
		logging.info("{} marked as noindex because it is a javascript resource".format(full_url))
		return url, {}, False, feeds, None, crawl_depth, average_crawl_speed

	if "/wp-json/" in full_url:
		print("{} marked as noindex because it is a wordpress api resource".format(full_url))
		logging.info("{} marked as noindex because it is a wordpress api resource".format(full_url))
		return url, {}, False, feeds, None, crawl_depth, average_crawl_speed

	if "?s=" in full_url:
		print("{} marked as noindex because it is a search result".format(full_url))
		logging.info("{} marked as noindex because it is a search result".format(full_url))
		return url, {}, False, feeds, None, crawl_depth, average_crawl_speed

	# Only get URLs that match namespace exactly
	in_matching_namespace = [s for s in namespaces_to_ignore if s.startswith(full_url.replace("http://", "").replace("https://", "").replace(site_url, "")) == full_url]

	nofollow_all = False

	# The next line of code skips indexing namespaces excluded in robots.txt
	if len(in_matching_namespace) < 2:
		# lastmod = final_urls[full_url]

		# If URL is not relative internal link and does not start with http:// or https://
		# Used to make sure link uses the right format

		# session = requests.Session()
		session.max_redirects = 3

		try:
			# Check if page is the right content type before indexing
			page_test = session.head(full_url, headers=config.HEADERS, allow_redirects=True, verify=False)

			# get redirect url
			if page_test.history and page_test.history[-1].url and page_test.history[-1].url != full_url:
				# skip redirects to external sites
				if not page_test.history[-1].url.startswith("http://" + site_url) and not page_test.history[-1].url.startswith("https://" + site_url):
					print("{} redirected to {}, which is on a different site, skipping".format(full_url, page_test.history[-1].url))
					logging.info("{} redirected to {}, which is on a different site, skipping".format(full_url, page_test.history[-1].url))
					return url, {}, False, feeds, None, crawl_depth, average_crawl_speed
					
				logging.error("{} redirected to {}".format(full_url, page_test.history[-1].url))
				print("{} redirected to {}".format(full_url, page_test.history[-1].url))

				full_url = page_test.history[-1].url

			if page_test.headers.get("x-robots-tag"):
				# only obey directives pointed at indieweb-search or everyone
				if "indieweb-search:" in page_test.headers.get("x-robots-tag") or ":" not in page_test.headers.get("x-robots-tag"):
					if "noindex" in page_test.headers.get("x-robots-tag") or "none" in page_test.headers.get("x-robots-tag"):
						print("{} marked as noindex".format(full_url))
						logging.info("{} marked as noindex".format(full_url))
						return url, {}, False, feeds, None, crawl_depth, average_crawl_speed
					elif "nofollow" in page_test.headers.get("x-robots-tag"):
						print("all links on {} marked as nofollow due to x-robots-tag nofollow value".format(full_url))
						logging.info("all links on {} marked as nofollow due to x-robots-tag nofollow value".format(full_url))
						nofollow_all = True
				
		except requests.exceptions.Timeout:
			logging.error("{} timed out, skipping".format(full_url))
			print("{} timed out, skipping".format(full_url))
			check_remove_url(full_url)
			return url, {}, False, feeds, None, crawl_depth, average_crawl_speed
		except requests.exceptions.TooManyRedirects:
			logging.error("{} too many redirects, skipping".format(full_url))
			print("{} too many redirects, skipping".format(full_url))
			check_remove_url(full_url)
			return url, {}, False, feeds, None, crawl_depth, average_crawl_speed
		except:
			logging.error("{} failed to connect, skipping".format(full_url))
			print("{} failed to connect, skipping".format(full_url))
			return url, {}, False, feeds, None, crawl_depth, average_crawl_speed

		# only index html documents

		if page_test.headers and page_test.headers.get("content-type") and "text/html" not in page_test.headers["content-type"]:
			print("{} is not a html resource, skipping".format(full_url))
			check_remove_url(full_url)
			logging.info("{} is not a html resource, skipping".format(full_url))
			return url, {}, False, feeds, None, crawl_depth, average_crawl_speed

		if page_test.headers.get("link"):
			header_links = requests.utils.parse_header_links(page_test.headers.get("link").rstrip('>').replace('>,<', ',<'))

			for link in header_links:
				if link["rel"] == "canonical":
					if link["rel"].startswith("/"):
						# get site domain
						domain = full_url.split("/")[2]
						link["rel"] = full_url.split("/")[0] + "//" + domain + link["rel"]

					canonical = link["rel"].strip("/").replace("http://", "https://").split("?")[0].lower()

					canonical_domain = canonical.split("/")[2]

					if canonical_domain.lower().replace("www.", "") != full_url.split("/")[2].lower().replace("www.", ""):
						print("{} has a canonical url of {}, not adding to queue because url points to a different domain".format(full_url, canonical))
						logging.info("{} has a canonical url of {}, not adding to queue because url points to a different domain".format(full_url, canonical))

						return url, {}, False, feeds, None, crawl_depth, average_crawl_speed

					if canonical and canonical != full_url.lower().strip("/").replace("http://", "https://").split("?")[0]:
						if discovered_urls.get(full_url).startswith("CANONICAL"):
							logging.info("{} has a canonical url of {}, not adding to index because the page was already identified as canonical".format(full_url, canonical))
							print("{} has a canonical url of {}, not adding to index because the page was already identified as canonicale".format(full_url, canonical))
						else:
							canonical_url = link["url"]

							iterate_list_of_urls.append(canonical_url)

							discovered_urls[canonical_url] = "CANONICAL {}".format(full_url)

							logging.info("{} has a canonical url of {}, skipping and added canonical URL to queue".format(full_url, canonical_url))
							print("{} has a canonical url of {}, skipping and added canonical URL to queue".format(full_url, canonical_url))

							return url, discovered_urls, False, None, crawl_depth, average_crawl_speed
		
		try:
			page = session.get(full_url, timeout=10, headers=config.HEADERS, allow_redirects=True, verify=False)
		except requests.exceptions.Timeout:
			logging.error("{} timed out, skipping".format(full_url))
			return url, {}, False, feeds, None, crawl_depth, average_crawl_speed
		except requests.exceptions.TooManyRedirects:
			logging.error("{} too many redirects, skipping".format(full_url))
			check_remove_url(full_url)
			return url, {}, False, feeds, None, crawl_depth, average_crawl_speed
		except:
			logging.error("{} failed to connect, skipping".format(full_url))
			return url, {}, False, feeds, None, crawl_depth, average_crawl_speed

		# 404 = not found, 410 = gone
		if page.status_code == 404 or page.status_code == 410:
			return url, {}, False, feeds, None, crawl_depth, average_crawl_speed

		elif page.status_code == 301 or page.status_code == 302 or page.status_code == 308:
			redirected_to = page.headers["Location"]
			
			if redirected_to:
				final_urls[redirected_to] = ""

				iterate_list_of_urls.append(redirected_to)

				# don't index a url if it was redirected from a canonical and wants to redirect again
				if discovered_urls.get(full_url) and discovered_urls.get(full_url).startswith("CANONICAL"):
					split_value = discovered_urls.get(full_url).split(" ")
					redirected_from = split_value[1]
					if redirected_from == redirected_to:
						print("{} has already been redirected from a canonical url, will not redirect a second time, skipping".format(full_url))
						logging.info("{} has already been redirected from a canonical url, will not redirect a second time, skipping".format(full_url))
						return url, {}, False, feeds, None, crawl_depth, average_crawl_speed

				discovered_urls[redirected_to] = redirected_to

			return url, {}, False, feeds
				
		elif page.status_code != 200:
			print("{} page returned {} status code".format(full_url, page.status_code))
			check_remove_url(full_url)
			logging.error("{} page {} status code".format(full_url, page.status_code))
			return url, {}, False, feeds, None, crawl_depth, average_crawl_speed

		if len(average_crawl_speed) > 10 and page.elapsed.total_seconds() > 2:
			print("WARNING: {} took {} seconds to load, server slow".format(full_url, page.elapsed.total_seconds()))
			logging.info("WARNING: {} took {} seconds to load, server slow".format(full_url, page.elapsed.total_seconds()))
		
		average_crawl_speed.append(page.elapsed.total_seconds())
		logging.info("{} took {} seconds to load".format(full_url, page.elapsed.total_seconds()))
		# only store the most recent 100 times
		average_crawl_speed = average_crawl_speed[:100]

		try:
			page_desc_soup = BeautifulSoup(page.content, "lxnl")
		except:
			page_desc_soup = BeautifulSoup(page.content, "html5lib")

		# get body of page
		# don't include head tag
		body = page_desc_soup.find("body")

		# get hash of web page
		hash = hashlib.sha256(str(body).encode('utf-8')).hexdigest()

		if web_page_hashes.get(hash):
			print("{} has already been indexed (hash the same as {}), skipping".format(full_url, web_page_hashes.get(hash)))
			logging.info("{} has already been indexed (hash the same as {}), skipping".format(full_url, web_page_hashes.get(hash)))
			return url, {}, False, feeds, hash, crawl_depth, average_crawl_speed

		# if http-equiv refresh redirect present
		# not recommended by W3C but still worth checking for just in case
		if page_desc_soup.find("meta", attrs={"http-equiv": "refresh"}):
			refresh_url = page_desc_soup.find("meta", attrs={"http-equiv": "refresh"})["content"].split(";")[1].split("=")[1]

			refresh_domain = refresh_url.split("/")[2]

			if refresh_domain.lower().replace("www.", "") != full_url.split("/")[2].lower().replace("www.", ""):
				print("{} has a refresh url of {}, not adding to queue because url points to a different domain".format(full_url, refresh_url))
				logging.info("{} has a refresh url of {}, not adding to queue because url points to a different domain".format(full_url, refresh_url))

				return url, {}, False, feeds, hash, crawl_depth, average_crawl_speed
				
			if refresh_url:
				final_urls[refresh_url] = ""

				iterate_list_of_urls.append(refresh_url)

				discovered_urls[refresh_url] = refresh_url

			# add new page to crawl queue so that previous validation can happen again (i.e. checking for canonical header)
			return url, {}, False, feeds, hash, crawl_depth, average_crawl_speed

		# check for canonical url

		if page_desc_soup.find("link", {"rel": "canonical"}):
			canonical_url = page_desc_soup.find("link", {"rel": "canonical"})["href"]

			if canonical_url and canonical_url.startswith("/"):
				# get site domain
				domain = full_url.split("/")[2]
				canonical_url = full_url.split("/")[0] + "//" + domain + canonical_url


			if canonical_url:
				canonical = canonical_url.strip("/").replace("http://", "https://").split("?")[0].lower()

				canonical_domain = canonical.split("/")[2]

				if canonical_domain.lower().replace("www.", "") != full_url.split("/")[2].lower().replace("www.", ""):
					print("{} has a canonical url of {}, not adding to queue because url points to a different domain".format(full_url, canonical))
					logging.info("{} has a canonical url of {}, not adding to queue because url points to a different domain".format(full_url, canonical))

					return url, {}, False, feeds, hash, crawl_depth, average_crawl_speed
				
				if canonical and canonical != full_url.lower().strip("/").replace("http://", "https://").split("?")[0]:
					if discovered_urls.get(full_url) and discovered_urls.get(full_url).startswith("CANONICAL"):
						logging.info("{} has a canonical url of {}, not adding to index because the page was already identified as canonical".format(full_url, canonical))
						print("{} has a canonical url of {}, not adding to index because the page was already identified as canonicale".format(full_url, canonical))
					else:
						final_urls[canonical] = ""

						iterate_list_of_urls.append(canonical)

						discovered_urls[canonical] = "CANONICAL"

						logging.info("{} has a canonical url of {}, skipping and added canonical URL to queue".format(full_url, canonical))
						print("{} has a canonical url of {}, skipping and added canonical URL to queue".format(full_url, canonical))

						return url, discovered_urls, False, feeds, hash, crawl_depth, average_crawl_speed

		check_if_no_index = page_desc_soup.find("meta", {"name":"robots"})

		if check_if_no_index and check_if_no_index.get("content") and ("noindex" in check_if_no_index.get("content") or "none" in check_if_no_index.get("content")):
			print("{} marked as noindex, skipping".format(full_url))
			logging.info("{} marked as noindex, skipping".format(full_url))
			return url, discovered_urls, False, feeds, hash, crawl_depth, average_crawl_speed

		elif check_if_no_index and check_if_no_index.get("content") and "nofollow" in check_if_no_index.get("content"):
			print("all links on {} marked as nofollow due to <meta> robots nofollow value".format(full_url))
			logging.info("all links on {} marked as nofollow due to <meta> robots nofollow value".format(full_url))
			nofollow_all = True

		# filter out pages marked as adult content
		if page_desc_soup.find("meta", {"name": "rating"}):
			if page_desc_soup.find("meta", {"name": "rating"}).get("content") == "adult" or \
				page_desc_soup.find("meta", {"name": "rating"}).get("content") == "RTA-5042-1996-1400-1577-RTA":
				print("{} marked as adult content in a meta tag, skipping".format(full_url))
				logging.info("{} marked as adult content in a meta tag, skipping".format(full_url))
				return url, discovered_urls, False, feeds, hash, crawl_depth, average_crawl_speed

		if nofollow_all == False:
			links = [l for l in page_desc_soup.find_all("a") if (l.get("rel") and "nofollow" not in l["rel"]) or (not l.get("rel") and l.get("href") not in ["#", "javascript:void(0);"])]
		else:
			links = []

		# only discover feeds and new links if a crawl is going on
		# this is used to ensure that the crawler doesn't discover new links or feeds when just indexing one page from a site that is already in the index
		if link_discovery == True:

			# check for feed with rel alternate
			# only support rss and atom right now

			if page_desc_soup.find_all("link", {"rel": "alternate"}):
				for feed_item in page_desc_soup.find_all("link", {"rel": "alternate"}):
					if feed_item and feed_item["href"].startswith("/"):
						# get site domain
						domain = full_url.split("/")[2]
						feed_url = full_url.split("/")[0] + "//" + domain + feed_item["href"]

						if feed_url and feed_url not in feed_urls:
							feeds, feed_urls = save_feed(site, full_url, feed_item["href"], feed_item.get("type"), feeds, feed_urls)
							
					elif feed_item and feed_item["href"].startswith("http"):
						if feed_item["href"] not in feed_urls and feed_item["href"].split("/")[2] == full_url.split("/")[2]:
							feeds, feed_urls = save_feed(site, full_url, feed_item["href"], feed_item.get("type"), feeds, feed_urls)
							
						elif feed_item["href"] not in feed_urls and feed_item["href"].split("/")[2] != full_url.split("/")[2]:
							print("found feed {}, but it points to a different domain, not saving".format(feed_item["href"]))
							logging.info("found feed {}, but it points to a different domain, not saving".format(feed_item["href"]))

					else:
						feeds, feed_urls = save_feed(site, full_url, full_url.strip("/") + "/" + feed_item["href"], feed_item.get("type"), feeds, feed_urls)

			# check if page has h-feed class on it
			# if a h-feed class is present, mark page as feed

			if page_desc_soup.select(".h-feed") and len(feeds) < 25:
				feeds.append({"website_url": site, "page_url": full_url, "feed_url": full_url, "mime_type": "h-feed", "etag": "NOETAG", "discovered": datetime.datetime.now().strftime("%Y-%m-%d")})
				feed_urls.append(full_url.strip("/"))
				# print("{} is a h-feed, will save to feeds.json".format(full_url))
				logging.info("{} is a h-feed, will save to feeds.json".format(full_url))

			# check for websub hub

			if page_desc_soup.find("link", {"rel": "hub"}) and len(feeds) < 25:
				websub_hub = page_desc_soup.find("link", {"rel": "hub"})["href"]

				websub_hub = websub_hub.strip().strip("<").strip(">")

				feeds.append({"website_url": site, "page_url": full_url, "feed_url": websub_hub, "mime_type": "websub", "etag": "NOETAG", "discovered": datetime.datetime.now().strftime("%Y-%m-%d")})
				
				feed_urls.append(full_url.strip("/"))

				# print("{} is a websub hub, will save to feeds.json".format(full_url))
				logging.info("{} is a websub hub, will save to feeds.json".format(full_url))

			# parse link headers
			link_headers = page.headers.get("Link")

			if link_headers:
				link_headers = link_headers.split(",")

				for link_header in link_headers:
					if "rel=\"hub\"" in link_header and len(feeds) < 25:
						websub_hub = link_header.split(";")[0].strip().strip("<").strip(">")

						feeds.append({"website_url": site, "page_url": full_url, "feed_url": websub_hub, "mime_type": "websub", "etag": "NOETAG", "discovered": datetime.datetime.now().strftime("%Y-%m-%d")})
						
						feed_urls.append(full_url.strip("/"))

						print("{} is a websub hub, will save to feeds.json".format(websub_hub))
						logging.info("{} is a websub hub, will save to feeds.json".format(websub_hub))

					if "rel=\"alternate\"" in link_header and len(feeds) < 25:
						original_feed_url = link_header.split(";")[0].strip().strip("<").strip(">").lower()

						if original_feed_url and original_feed_url not in feed_urls:
							# get feed type
							if "type=\"" in link_header:
								feed_type = link_header.split("type=\"")[1].split("\"")[0]
							else:
								feed_type = "feed"

							if original_feed_url.startswith("/"):
								# get site domain
								domain = full_url.split("/")[2]
								feed_url = full_url.split("/")[0] + "//" + domain + original_feed_url

								if feed_url and feed_url not in feed_urls:
									feeds, feed_urls = save_feed(site, full_url, original_feed_url, feed_type, feeds, feed_urls)
							elif original_feed_url.startswith("http"):
								if original_feed_url not in feed_urls and original_feed_url.split("/")[2] == full_url.split("/")[2]:
									feeds, feed_urls = save_feed(site, full_url, original_feed_url, feed_type, feeds, feed_urls)
							else:
								feeds, feed_urls = save_feed(site, full_url, original_feed_url, feed_type, feeds, feed_urls)

			final_urls, iterate_list_of_urls, all_links, external_links, discovered_urls = page_link_discovery.page_link_discovery(links, final_urls, iterate_list_of_urls, full_url, all_links, external_links, discovered_urls, site_url, crawl_depth)

		# there are a few wikis in the crawl and special pages provide very little value to the search index
		if "/Special:" in full_url and "MediaWiki" in page_desc_soup.find("meta", {"name": "generator"})["content"]:
			print("{} is a mediawiki special page, will not crawl".format(full_url))
			logging.info("{} is a mediawiki special page, will not crawl".format(full_url))
			return url, {}, False, feeds, hash, crawl_depth, average_crawl_speed

		if "/tags/" in full_url or "/tag/" in full_url or "/label/" in full_url or "/search/" in full_url or "/category/" in full_url or "/categories/" in full_url:
			print("{} marked as follow, noindex because it is a tag, label, or search resource".format(full_url))
			logging.info("{} marked as follow, noindex because it is a tag, label, or search resource".format(full_url))
			return url, {}, False, feeds, hash, crawl_depth, average_crawl_speed

		elif "/page/" in full_url and full_url.split("/")[-1].isdigit():
			print("{} marked as follow, noindex because it is a page archive".format(full_url))
			logging.info("{} marked as follow, noindex because it is a page archive".format(full_url))
			return url, {}, False, feeds, hash, crawl_depth, average_crawl_speed

		thin_content = False

		# 20 word minimum will prevent against short notes
		if page_desc_soup.select(".e-content"):
			page_text = page_desc_soup.select(".e-content")[0]
			# print(page_text)
			# if len(page_text.get_text().split(" ")) < 75:
			# 	print("content on {} is thin (under 75 words in e-content), marking as thin_content".format(full_url))
			# 	logging.info("content on {} is thin (under 75 words in e-content), marking as thin_content".format(full_url))
			# 	thin_content = True

		elif page_desc_soup.select(".h-entry"):
			page_text = page_desc_soup.select(".h-entry")[0]
			# print(page_text)
			# if len(page_text.get_text().split(" ")) < 75:
			# 	print("content on {} is thin (under 75 words in h-entry), marking as thin_content".format(full_url))
			# 	logging.info("content on {} is thin (under 75 words in h-entry), marking as thin_content".format(full_url))
			# 	thin_content = True

		elif page_desc_soup.find("main"):
			page_text = page_desc_soup.find("main")
		elif page_desc_soup.find("div", {"id": "main"}):
			page_text = page_desc_soup.find("div", {"id": "main"})
		elif page_desc_soup.find("div", {"id": "app"}):
			page_text = page_desc_soup.find("div", {"id": "app"})
		elif page_desc_soup.find("div", {"id": "page"}):
			page_text = page_desc_soup.find("div", {"id": "page"})
		elif page_desc_soup.find("div", {"id": "site-container"}):
			page_text = page_desc_soup.find("div", {"id": "main"})
		elif page_desc_soup.find("div", {"id": "site-container"}):
			page_text = page_desc_soup.find("div", {"id": "application-main"})
		else:
			page_text = page_desc_soup.find("body")

		if page_text == None:
			return url, discovered_urls, False, feeds, hash, crawl_depth, average_crawl_speed

		# word count is slightly higher if e-content or h-entry could not be found because this count will consider other parts of a page
		if page_text.text and len(page_text.text.split(" ")) < 100:
			print("content on {} is thin (under 100 words), marking as thin_content".format(full_url))
			logging.info("content on {} is thin (under 100 words), marking as thin_content".format(full_url))
			thin_content = True

		heading_info = {
			"h1": [],
			"h2": [],
			"h3": [],
			"h4": [],
			"h5": [],
			"h6": []
		}

		for k, v in heading_info.items():
			if page_text.find_all(k):
				for h in page_text.find_all(k):
					v.append(h.text)

		# Only index if noindex attribute is not present

		page_text, page_desc_soup, published_on, meta_description, doc_title, noindex = crawler.page_info.get_page_info(page_text, page_desc_soup, full_url, homepage_meta_description)

		if noindex == True:
			return url, discovered_urls, False, feeds, hash, crawl_depth, average_crawl_speed

		# get number of links
		
		links = page_desc_soup.find_all("a")
		number_of_links = len(links)
		word_count = len(page_desc_soup.get_text().split())

		# if the ratio of words to links < 3:1, do not index
		# these pages may be spam or other non-content pages that will not be useful to those using the search engine
		if word_count and (word_count > 0 and number_of_links and number_of_links > 0) and word_count > 200 and word_count / number_of_links < 3:
			thin_content = True
			
		count += 1

		if check_if_no_index and check_if_no_index.get("content") and "noindex" in check_if_no_index.get("content"):
			print("{} marked as noindex, skipping".format(full_url))
			logging.info("{} marked as noindex, skipping".format(full_url))
			return url, discovered_urls, False, feeds, hash, crawl_depth, average_crawl_speed
			
		try:
			pages_indexed = add_to_database.add_to_database(full_url, published_on, doc_title, meta_description, heading_info, page, pages_indexed, page_desc_soup, len(links), crawl_budget, nofollow_all, page_desc_soup.find("body"), h_card, hash, thin_content)
		except Exception as e:
			print("error with {}".format(full_url))
			print(e)
			logging.warning("error with {}".format(full_url))
			logging.warning(e)

	print('finished {}'.format(full_url))

	return url, discovered_urls, True, feeds, hash, crawl_depth, average_crawl_speed