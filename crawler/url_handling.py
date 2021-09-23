from bs4 import BeautifulSoup, Comment
import requests
import datetime
import logging
import config
import crawler.page_info
import crawler.image_handling
import hashlib
import json

yesterday = datetime.datetime.today() - datetime.timedelta(days=1)

def add_to_database(full_url, published_on, doc_title, meta_description, category, heading_info, page, pages_indexed, page_content, outgoing_links, crawl_budget, reindex):
	# get last modified date

	if page != "" and page.headers:
		length = page.headers.get("content-length")
	else:
		length = len(page_content)

	# remove script and style tags from page_content

	for script in page_content(["script", "style"]):
		script.decompose()

	#remove comments

	comments = page_content.findAll(text=lambda text:isinstance(text, Comment))
	[comment.extract() for comment in comments]

	md5_hash = hashlib.md5(str("".join([w for w in page_content.get_text().split(" ")[:200]])).encode("utf-8")).hexdigest()

	# check if md5 hash in posts

	r = requests.post("https://es-indieweb-search.jamesg.blog/check?hash={}".format(md5_hash), headers={"Authorization": "Bearer {}".format(config.ELASTICSEARCH_API_TOKEN)})

	if r.status_code == 200:
		if r.json() and len(r.json()) > 0 and r.json()["url"] != full_url:
			print("content duplicate of existing record, skipping")
			return pages_indexed

	if type(published_on) == dict and published_on.get("datetime") != None:
		date_to_record = published_on["datetime"].split("T")[0]
	else:
		date_to_record = ""

	record = {
		"title": doc_title,
		"meta_description": meta_description,
		"url": full_url,
		"published_on": date_to_record,
		"category": category,
		"h1": ", ".join(heading_info["h1"]),
		"h2": ", ".join(heading_info["h2"]),
		"h3": ", ".join(heading_info["h3"]),
		"h4": ", ".join(heading_info["h4"]),
		"h5": ", ".join(heading_info["h5"]),
		"h6": ", ".join(heading_info["h6"]),
		"length": length,
		"important_phrases": "",
		"page_content": str(page_content),
		"incoming_links": 0,
		"page_text": page_content.get_text(),
		"outgoing_links": outgoing_links,
		"domain": full_url.split("/")[2],
		"word_count": len(page_content.get_text().split(" ")),
		"md5_hash": md5_hash,
		"last_crawled": datetime.datetime.today().strftime("%Y-%m-%d %H:%M:%S"),
		"referring_domains_to_site": 0, # updated when index is rebuilt
		"internal_incoming_links": 0 # not actively used
	}

	# results currently being saved to a file, so no need to run this code

	# check_if_indexed = requests.post("https://es-indieweb-search.jamesg.blog/check?url={}".format(full_url), headers={"Authorization": "Bearer {}".format(config.ELASTICSEARCH_API_TOKEN)}).json()

	# if len(check_if_indexed) > 0:
	# 	record["incoming_links"] = check_if_indexed[0]["_source"]["incoming_links"]
	# else:
	# 	record["incoming_links"] = 0

	# save to json file

	with open("results.json".format(md5_hash), "a+") as f:
		f.write(json.dumps(record))
		f.write("\n")

	# if len(check_if_indexed) == 0:
	# 	r = requests.post("https://es-indieweb-search.jamesg.blog/create", headers={"Authorization": "Bearer {}".format(config.ELASTICSEARCH_API_TOKEN)}, json=record)
	# else:
	# 	r = requests.post("https://es-indieweb-search.jamesg.blog/update", headers={"Authorization": "Bearer {}".format(config.ELASTICSEARCH_API_TOKEN)}, json=record)
	# 	print("updated page {} ({}/{})".format(full_url, pages_indexed, crawl_budget))

	print("indexed new page {} ({}/{})".format(full_url, pages_indexed, crawl_budget))
	logging.info("indexed new page {} ({}/{})".format(full_url, pages_indexed, crawl_budget))

	pages_indexed += 1

	return pages_indexed

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

def crawl_urls(final_urls, namespaces_to_ignore, pages_indexed, all_links, external_links, discovered_urls, iterate_list_of_urls, site_url, crawl_budget, url, reindex):
	"""
		Crawls URLs in list, adds URLs to index, and returns updated list
	"""
	count = 0

	full_url = url.replace("http://", "https://")

	if len(full_url) > 125:
		print("{} url too long, skipping".format(full_url))
		logging.info("{} url too long, skipping".format(full_url))
		return url, {}, False, []

	if "javascript:" in full_url:
		print("{} marked as follow, noindex because it is a javascript resource".format(full_url))
		logging.info("{} marked as follow, noindex because it is a javascript resource".format(full_url))
		return url, {}, False, []

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
			return url, {}, False, []
		except requests.exceptions.TooManyRedirects:
			logging.error("{} too many redirects, skipping".format(full_url))
			print("{} too many redirects, skipping".format(full_url))
			check_remove_url(full_url)
			return url, {}, False, []
		except:
			logging.error("{} failed to connect, skipping".format(full_url))
			print("{} failed to connect, skipping".format(full_url))
			return url, {}, False, []

		if page_test.headers and page_test.headers.get("content-type") and "text/html" not in page_test.headers["content-type"] and "text/plain" not in page_test.headers["content-type"]:
			print("{} is not a html resource, skipping".format(full_url))
			check_remove_url(full_url)
			logging.info("{} is not a html resource, skipping".format(full_url))
			return url, {}, False, []

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

						return url, discovered_urls, False, []

		session = requests.Session()
		session.max_redirects = 3

		try:
			page = session.get(full_url, timeout=10, headers=config.HEADERS, allow_redirects=True, verify=False)
		except requests.exceptions.Timeout:
			logging.error("{} timed out, skipping".format(full_url))
			return url, {}, False, []
		except requests.exceptions.TooManyRedirects:
			logging.error("{} too many redirects, skipping".format(full_url))
			check_remove_url(full_url)
			return url, {}, False, []
		except:
			logging.error("{} failed to connect, skipping".format(full_url))
			return url, {}, False, []

		if page.status_code == 404:
			return url, {}, False, []

		elif page.status_code == 301 or page.status_code == 302 or page.status_code == 308:
			redirected_to = page.headers["Location"]
			
			if redirected_to:
				final_urls[redirected_to] = ""

				iterate_list_of_urls.append(redirected_to)

				discovered_urls[redirected_to] = redirected_to

			return url, {}, False, []
				
		elif page.status_code != 200:
			print("{} page failed to load.".format(full_url))
			check_remove_url(full_url)
			logging.error("{} page failed to load.".format(full_url))
			return url, {}, False, []

		try:
			page_desc_soup = BeautifulSoup(page.content, "html5lib")
		except:
			page_desc_soup = BeautifulSoup(page.content, "lxml")

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

				return url, discovered_urls, False, []

		check_if_no_index = page_desc_soup.find("meta", {"name":"robots"})

		if check_if_no_index and check_if_no_index.get("content") and ("noindex" in check_if_no_index.get("content") or "none" in check_if_no_index.get("content")):
			print("{} marked as noindex, skipping".format(full_url))
			logging.info("{} marked as noindex, skipping".format(full_url))
			return url, {}, False, []

		elif check_if_no_index and check_if_no_index.get("content") and "nofollow" in check_if_no_index.get("content"):
			print("all links on {} marked as nofollow due to <meta> robots nofollow value".format(full_url))
			logging.info("all links on {} marked as nofollow due to <meta> robots nofollow value".format(full_url))
			nofollow_all = True

		if nofollow_all == False:
			links = [l for l in page_desc_soup.find_all("a") if (l.get("rel") and "nofollow" not in l["rel"]) or (not l.get("rel") and l.get("href") not in ["#", "javascript:void(0);"])]
		else:
			links = []

		# check if indexed
		# check_if_indexed = requests.post("https://es-indieweb-search.jamesg.blog/check?url={}".format(full_url), headers={"Authorization": "Bearer {}".format(config.ELASTICSEARCH_API_TOKEN)}).json()

		# # get todays date
		# today = datetime.datetime.now()

		# # get date two weeks ago
		# two_weeks_ago = today - datetime.timedelta(days=14)

		# if len(check_if_indexed) > 0:
		# 	# if page was crawled after result of last-modified header, don't crawl page again
		# 	if check_if_indexed and check_if_indexed[0]["_source"].get("last_crawled") and check_if_indexed["last_crawled"] <= page.headers.get("last-modified"):
		# 		logging.info("{} was crawled after last-modified header, skipping".format(full_url))
		# 		print("{} was crawled after last-modified header, skipping".format(full_url))
		# 		return url, {}, False, all_links

			# elif check_if_indexed and check_if_indexed[0].get("last_crawled") < two_weeks_ago:
			# 	logging.info("{} was crawled less than two weeks ago, skipping".format(full_url))
			# 	print("{} was crawled less than two weeks ago, skipping".format(full_url))
			# 	return url, {}, False, all_links

		final_urls, iterate_list_of_urls, all_links, external_links, discovered_urls = page_link_discovery(links, final_urls, iterate_list_of_urls, full_url, all_links, external_links, discovered_urls, site_url)

		if "/tags/" in full_url or "/tag/" in full_url or "/label/" in full_url or "/search/" in full_url or "/category/" in full_url or "/categories/" in full_url:
			print("{} marked as follow, noindex because it is a tag, label, or search resource".format(full_url))
			logging.info("{} marked as follow, noindex because it is a tag, label, or search resource".format(full_url))
			return url, {}, False, all_links

		elif "/page/" in full_url and full_url.split("/")[-1].isdigit():
			print("{} marked as follow, noindex because it is a page archive".format(full_url))
			logging.info("{} marked as follow, noindex because it is a page archive".format(full_url))
			return url, {}, False, all_links

		# 20 word minimum will prevent against short notes
		if page_desc_soup.select("e-content"):
			page_text = page_desc_soup.select("e-content")[0]
			if len(page_text.get_text().split(" ")) < 10:
				print("content on {} is thin (under 10 words in e-content), skipping")
				logging.info("content on {} is thin (under 10 words in e-content), skipping".format(full_url))
				return url, {}, False, all_links
		elif page_desc_soup.select("h-entry"):
			page_text = page_desc_soup.select("h-entry")
			if len(page_text.get_text().split(" ")) < 10:
				print("content on {} is thin (under 10 words in h-entry), skipping")
				logging.info("content on {} is thin (under 10 words in h-entry), skipping".format(full_url))
				return url, {}, False, all_links
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
			return url, discovered_urls, False, all_links

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

		# Discover new links that might be on a page to follow later

		# Only index if noindex attribute is not present
		page_text, page_desc_soup, published_on, meta_description, doc_title, category, remove_doc_title_from_h1_list, noindex = crawler.page_info.get_page_info(page_text, page_desc_soup, full_url)

		if noindex == True:
			return url, discovered_urls, False, all_links

		if remove_doc_title_from_h1_list == True:
			heading_info["h1"] = heading_info["h1"].remove(doc_title)
			
		count += 1

		if check_if_no_index and check_if_no_index.get("content") and "noindex" in check_if_no_index.get("content"):
			print("{} marked as noindex, skipping".format(full_url))
			logging.info("{} marked as noindex, skipping".format(full_url))
			return url, discovered_urls, False, links
			
		try:
			pages_indexed = add_to_database(full_url, published_on, doc_title, meta_description, category, heading_info, page, pages_indexed, page_text, len(links), crawl_budget, reindex)
		except Exception as e:
			print("error with {}".format(full_url))
			print(e)
			logging.warning("error with {}".format(full_url))
			logging.warning(e)

	print('finished {}'.format(full_url))

	return url, discovered_urls, True, all_links

def page_link_discovery(links, final_urls, iterate_list_of_urls, page_being_processed, all_links, external_links, discovered_urls, site_url):
	"""
		Finds all the links on the page and adds them to the list of links to crawl.
	"""

	discovered_urls = {}

	for link in links:
		if link.get("href"):
			if "://" in link.get("href") and len(link.get("href").split("://")) > 0 and link.get("href").split("://")[0] != "https" and link.get("href").split(":")[0] != "http":
				# url is wrong protocol, continue
				continue

			link["href"] = link["href"].split("?")[0]

			if link["href"].startswith("//"):
				all_links.append([page_being_processed, link.get("href"), datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "external"])
				external_links["https://" + link["href"]] = page_being_processed
				continue

			if "@" in link["href"]:
				continue

			# Add start of URL to end of any links that don't have it
			elif link["href"].startswith("/"):
				full_link = "https://{}".format(site_url) + link["href"]
			elif link["href"].startswith("http"):
				full_link = link["href"]
			elif "//" in link["href"] and "http" not in link["href"]:
				continue
			else:
				if ".." not in link["href"]:
					full_link = "{}/{}".format("/".join(page_being_processed.split("/")[:-1]), link["href"])
				else:
					continue

			if "?" in full_link:
				full_link = full_link[:full_link.index("?")]

			if full_link.endswith("//"):
				full_link = full_link[:-1]

			if "./" in full_link:
				full_link = full_link.replace("./", "")

			if full_link not in final_urls.keys() \
			and "#" not in full_link \
			and (full_link.startswith("https://{}".format(site_url)) or full_link.startswith("http://{}".format(site_url))) \
			and ".xml" not in full_link \
			and ".pdf" not in full_link \
			and not full_link.startswith("//") \
			and len(final_urls) < 1000:
			# and ((reindex == True and len(page_being_processed.replace("https://").strip("/").split("/")) == 0) or reindex == False):
				all_links.append([page_being_processed, link.get("href"), datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "internal", link.text])
				print("indexing queue now contains " + full_link)
				logging.debug("indexing queue now contains " + full_link)
				final_urls[full_link] = ""

				iterate_list_of_urls.append(full_link)

				discovered_urls[full_link] = page_being_processed

	return final_urls, iterate_list_of_urls, all_links, external_links, discovered_urls