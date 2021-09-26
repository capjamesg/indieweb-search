from bs4 import BeautifulSoup
import requests
import datetime
import logging
import config
import crawler.page_info
import crawler.add_to_database as add_to_database
import crawler.discovery as page_link_discovery

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

def crawl_urls(final_urls, namespaces_to_ignore, pages_indexed, all_links, external_links, discovered_urls, iterate_list_of_urls, site_url, crawl_budget, url, feeds, link_discovery=True):
	"""
		Crawls URLs in list, adds URLs to index, and returns updated list
	"""
	count = 0

	full_url = url.replace("http://", "https://")

	if len(full_url) > 125:
		print("{} url too long, skipping".format(full_url))
		logging.info("{} url too long, skipping".format(full_url))
		return url, {}, False

	if "javascript:" in full_url:
		print("{} marked as follow, noindex because it is a javascript resource".format(full_url))
		logging.info("{} marked as follow, noindex because it is a javascript resource".format(full_url))
		return url, {}, False

	# Only get URLs that match namespace exactly
	in_matching_namespace = [s for s in namespaces_to_ignore if s.startswith(full_url.replace("http://", "").replace("https://", "").replace(site_url, "")) == full_url]

	nofollow_all = False

	# The next line of code skips indexing namespaces excluded in robots.txt
	if len(in_matching_namespace) < 2:
		# lastmod = final_urls[full_url]

		# If URL is not relative internal link and does not start with http:// or https://
		# Used to make sure link uses the right format

		session = requests.Session()
		session.max_redirects = 3

		try:
			# Check if page is the right content type before indexing
			page_test = session.head(full_url, headers=config.HEADERS, allow_redirects=True, verify=False)

			# get redirect url
			if page_test.history:
				logging.error("{} redirected to {}".format(full_url, page_test.history[0].url))
				print("{} redirected to {}".format(full_url, page_test.history[0].url))
				full_url = page_test.history[0].url

			if page_test.headers.get("X-Robots-Tag"):
				# only obey directives pointed at indieweb-search or everyone
				if "indieweb-search:" in page_test.headers.get("X-Robots-Tag") or ":" not in page_test.headers.get("X-Robots-Tag"):
					if "noindex" in page_test.headers.get("X-Robots-Tag") or "none" in page_test.headers.get("X-Robots-Tag"):
						print("{} marked as noindex".format(full_url))
						logging.info("{} marked as noindex".format(full_url))
						return url, {}, False, []
					elif "nofollow" in page_test.headers.get("X-Robots-Tag"):
						print("all links on {} marked as nofollow due to X-Robots-Tag nofollow value".format(full_url))
						logging.info("all links on {} marked as nofollow due to X-Robots-Tag nofollow value".format(full_url))
						nofollow_all = True
				
		except requests.exceptions.Timeout:
			logging.error("{} timed out, skipping".format(full_url))
			print("{} timed out, skipping".format(full_url))
			check_remove_url(full_url)
			return url, {}, False
		except requests.exceptions.TooManyRedirects:
			logging.error("{} too many redirects, skipping".format(full_url))
			print("{} too many redirects, skipping".format(full_url))
			check_remove_url(full_url)
			return url, {}, False
		except:
			logging.error("{} failed to connect, skipping".format(full_url))
			print("{} failed to connect, skipping".format(full_url))
			return url, {}, False

		if page_test.headers and page_test.headers.get("content-type") and "text/html" not in page_test.headers["content-type"] and "text/plain" not in page_test.headers["content-type"]:
			print("{} is not a html resource, skipping".format(full_url))
			check_remove_url(full_url)
			logging.info("{} is not a html resource, skipping".format(full_url))
			return url, {}, False

		if page_test.headers.get("link"):
			header_links = requests.utils.parse_header_links(page_test.headers.get("link").rstrip('>').replace('>,<', ',<'))

			for link in header_links:
				if link["rel"] == "canonical":
					if link["rel"].startswith("/"):
						# get site domain
						domain = full_url.split("/")[2]
						link["rel"] = "https://" + domain + link["rel"]

					canonical = link["rel"].strip("/").replace("http://", "https://").split("?")[0]

					if canonical and canonical != full_url.lower().strip("/").replace("http://", "https://").split("?")[0]:
						canonical_url = link["url"]

						iterate_list_of_urls.append(canonical_url)

						discovered_urls[canonical_url] = canonical_url

						logging.info("{} has a canonical url of {}, skipping and added canonical URL to queue".format(full_url, canonical_url))
						print("{} has a canonical url of {}, skipping and added canonical URL to queue".format(full_url, canonical_url))

						return url, discovered_urls, False

		session = requests.Session()
		session.max_redirects = 3

		try:
			page = session.get(full_url, timeout=10, headers=config.HEADERS, allow_redirects=True, verify=False)
		except requests.exceptions.Timeout:
			logging.error("{} timed out, skipping".format(full_url))
			return url, {}, False
		except requests.exceptions.TooManyRedirects:
			logging.error("{} too many redirects, skipping".format(full_url))
			check_remove_url(full_url)
			return url, {}, False
		except:
			logging.error("{} failed to connect, skipping".format(full_url))
			return url, {}, False

		# 404 = not found, 410 = gone
		if page.status_code == 404 or page.status_code == 410:
			return url, {}, False

		elif page.status_code == 301 or page.status_code == 302 or page.status_code == 308:
			redirected_to = page.headers["Location"]
			
			if redirected_to:
				final_urls[redirected_to] = ""

				iterate_list_of_urls.append(redirected_to)

				discovered_urls[redirected_to] = redirected_to

			return url, {}, False
				
		elif page.status_code != 200:
			print("{} page failed to load.".format(full_url))
			check_remove_url(full_url)
			logging.error("{} page failed to load.".format(full_url))
			return url, {}, False

		try:
			page_desc_soup = BeautifulSoup(page.content, "html5lib")
		except:
			page_desc_soup = BeautifulSoup(page.content, "lxml")

		# if http-equiv refresh redirect present
		# not recommended by W3C but still worth checking for just in case
		if page_desc_soup.find("meta", attrs={"http-equiv": "refresh"}):
			refresh_url = page_desc_soup.find("meta", attrs={"http-equiv": "refresh"})["content"].split(";")[1].split("=")[1]

			if refresh_url:
				final_urls[refresh_url] = ""

				iterate_list_of_urls.append(refresh_url)

				discovered_urls[refresh_url] = refresh_url

			# add new page to crawl queue so that previous validation can happen again (i.e. checking for canonical header)
			return url, {}, False, []

		# check for canonical url

		if page_desc_soup.find("link", {"rel": "canonical"}):
			canonical_url = page_desc_soup.find("link", {"rel": "canonical"})["href"]
			if canonical_url.startswith("/"):
				# get site domain
				domain = full_url.split("/")[2]
				canonical_url = "https://" + domain + canonical_url

			canonical = canonical_url.strip("/").replace("http://", "https://").split("?")[0]
			
			if canonical and canonical != full_url.lower().strip("/").replace("http://", "https://").split("?")[0]:
				final_urls[canonical_url] = ""

				iterate_list_of_urls.append(canonical_url)

				discovered_urls[canonical_url] = canonical_url

				logging.info("{} has a canonical url of {}, skipping and added canonical URL to queue".format(full_url, canonical_url))
				print("{} has a canonical url of {}, skipping and added canonical URL to queue".format(full_url, canonical_url))

				return url, discovered_urls, False

		check_if_no_index = page_desc_soup.find("meta", {"name":"robots"})

		if check_if_no_index and check_if_no_index.get("content") and ("noindex" in check_if_no_index.get("content") or "none" in check_if_no_index.get("content")):
			print("{} marked as noindex, skipping".format(full_url))
			logging.info("{} marked as noindex, skipping".format(full_url))
			return url, {}, False

		elif check_if_no_index and check_if_no_index.get("content") and "nofollow" in check_if_no_index.get("content"):
			print("all links on {} marked as nofollow due to <meta> robots nofollow value".format(full_url))
			logging.info("all links on {} marked as nofollow due to <meta> robots nofollow value".format(full_url))
			nofollow_all = True

		if nofollow_all == False:
			links = [l for l in page_desc_soup.find_all("a") if (l.get("rel") and "nofollow" not in l["rel"]) or (not l.get("rel") and l.get("href") not in ["#", "javascript:void(0);"])]
		else:
			links = []

		# check for feed with rel alternate
		# only support rss and atom right now
		# link_discovery = False when crawling with feed discovery
		# using link_discovery = False to avoid searching for feeds too
		if link_discovery == True:
			if page_desc_soup.find("link", {"rel": "alternate", "type": "application/rss+xml"}):
				feed_url = page_desc_soup.find("link", {"rel": "alternate", "type": "application/rss+xml"})["href"]
				
				if feed_url.startswith("/"):
					# get site domain
					domain = full_url.split("/")[2]
					feed_url = "https://" + domain + feed_url

				canonical = feed_url.strip("/").replace("http://", "https://").split("?")[0]

				if not feeds.get(feed_url):
					with open("feeds.txt", "a+") as f:
						# NOETAG is substitute value
						# if none is provided, feed validation will fail
						f.write("{}, NOETAG\n".format(feed_url))

			elif page_desc_soup.find("link", {"rel": "alternate", "type": "application/atom+xml"}):
				feed_url = page_desc_soup.find("link", {"rel": "alternate", "type": "application/atom+xml"})["href"]

				if feed_url.startswith("/"):
					# get site domain
					domain = full_url.split("/")[2]
					feed_url = "https://" + domain + feed_url

				canonical = feed_url.strip("/").replace("http://", "https://").split("?")[0]

				if not feeds.get(feed_url):
					with open("feeds.txt", "a+") as f:
						f.write("{}, NOETAG\n".format(feed_url))

			# check if page has h-feed class on it
			# if a h-feed class is present, mark page as feed
			if page_desc_soup.select("[class*=h-feed]"):

				print("*" * 45)
				if not feeds.get(feed_url):
					with open("feeds.txt", "a+") as f:
						f.write("{}, NOETAG\n".format(full_url))

		if link_discovery == True:
			final_urls, iterate_list_of_urls, all_links, external_links, discovered_urls = page_link_discovery.page_link_discovery(links, final_urls, iterate_list_of_urls, full_url, all_links, external_links, discovered_urls, site_url)

		if "/tags/" in full_url or "/tag/" in full_url or "/label/" in full_url or "/search/" in full_url or "/category/" in full_url or "/categories/" in full_url:
			print("{} marked as follow, noindex because it is a tag, label, or search resource".format(full_url))
			logging.info("{} marked as follow, noindex because it is a tag, label, or search resource".format(full_url))
			return url, {}, False

		elif "/page/" in full_url and full_url.split("/")[-1].isdigit():
			print("{} marked as follow, noindex because it is a page archive".format(full_url))
			logging.info("{} marked as follow, noindex because it is a page archive".format(full_url))
			return url, {}, False

		# 20 word minimum will prevent against short notes
		if page_desc_soup.select("e-content"):
			page_text = page_desc_soup.select("e-content")[0]
			if len(page_text.get_text().split(" ")) < 10:
				print("content on {} is thin (under 10 words in e-content), skipping")
				logging.info("content on {} is thin (under 10 words in e-content), skipping".format(full_url))
				return url, {}, False

		elif page_desc_soup.select("h-entry"):
			page_text = page_desc_soup.select("h-entry")
			if len(page_text.get_text().split(" ")) < 10:
				print("content on {} is thin (under 10 words in h-entry), skipping")
				logging.info("content on {} is thin (under 10 words in h-entry), skipping".format(full_url))
				return url, {}, False
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
			return url, discovered_urls, False

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
		page_text, page_desc_soup, published_on, meta_description, doc_title, noindex = crawler.page_info.get_page_info(page_text, page_desc_soup, full_url)

		if noindex == True:
			return url, discovered_urls, False
			
		count += 1

		if check_if_no_index and check_if_no_index.get("content") and "noindex" in check_if_no_index.get("content"):
			print("{} marked as noindex, skipping".format(full_url))
			logging.info("{} marked as noindex, skipping".format(full_url))
			return url, discovered_urls, False
			
		try:
			pages_indexed = add_to_database.add_to_database(full_url, published_on, doc_title, meta_description, heading_info, page, pages_indexed, page_desc_soup, len(links), crawl_budget, nofollow_all, page_text, page_desc_soup, site_url, page_desc_soup.find("body"))
		except Exception as e:
			print("error with {}".format(full_url))
			print(e)
			logging.warning("error with {}".format(full_url))
			logging.warning(e)

	print('finished {}'.format(full_url))

	return url, discovered_urls, True