from elasticsearch_server import check
from bs4 import BeautifulSoup
import requests
import datetime
import logging
import config
import crawler.page_info
import crawler.image_handling
import hashlib

yesterday = datetime.datetime.today() - datetime.timedelta(days=1)

def log_error(page_url, status_code, message, discovered_urls, broken_urls, discovered=None):
	return
	# This logic is necessary as I do pass a discovered value for image errors
	if discovered == None:
		if discovered_urls.get(page_url):
			# Some links will be discovered through other links instead of the sitemap
			discovered = discovered_urls[page_url]
		else:
			discovered = "Sitemap"

	# Page is already validated by this point so I use 200 for the status code
	broken_urls.append(
		{
			"url": page_url,
			"status_code": status_code,
			"message": message,
			"discovered": discovered
		}
	)

def add_to_database(full_url, published_on, doc_title, meta_description, category, heading_info, page, important_phrases, pages_indexed, page_content, outgoing_links):
	# check_if_indexed = cursor.execute("SELECT COUNT(url) FROM posts WHERE url = ?", (full_url,)).fetchone()[0]

	# lemmatize page content so the index uses root words rather than exact words
	#page_content = page_content

	if page != "" and page.headers:
		length = page.headers.get("content-length")
	else:
		length = len(page_content)

	md5_hash = hashlib.md5(str(page_content).encode("utf-8")).hexdigest()

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
		"page_text": page_content.get_text(),
		"incoming_links": 0,
		"outgoing_links": outgoing_links,
		"page_rank": 0,
		"domain": full_url.split("/")[2],
		"word_count": len(page_content.get_text().split(" ")),
		"md5_hash": md5_hash,
	}

	check_if_indexed = requests.post("https://es-indieweb-search.jamesg.blog/check?url={}".format(full_url), headers={"Authorization": "Bearer {}".format(config.ELASTICSEARCH_API_TOKEN)}).json()
	
	if len(check_if_indexed) == 0:
		r = requests.post("https://es-indieweb-search.jamesg.blog/create", headers={"Authorization": "Bearer {}".format(config.ELASTICSEARCH_API_TOKEN)}, json=record)
		print("indexed new page {}".format(full_url))
	else:
		r = requests.post("https://es-indieweb-search.jamesg.blog/update", headers={"Authorization": "Bearer {}".format(config.ELASTICSEARCH_API_TOKEN)}, json=record)
		print("updated page {}".format(full_url))
		logging.debug("updating {} post as post already indexed".format(full_url))

	pages_indexed += 1

	return pages_indexed

def crawl_urls(final_urls, namespaces_to_ignore, pages_indexed, images_indexed, image_urls, all_links, external_links, discovered_urls, broken_urls, iterate_list_of_urls, site_url, crawl_budget):
	"""
		Crawls URLs in list, adds URLs to index, and returns updated list
	"""
	count = 0
	for full_url in iterate_list_of_urls:
		# if full_url[-1] != "/":
		# 	full_url = full_url + "/"
		full_url = full_url.replace("http://", "https://")
		if ".pdf" in full_url:
			continue
		
		if count == crawl_budget:
			break

		print(count)

		# Only get URLs that match namespace exactly
		in_matching_namespace = [s for s in namespaces_to_ignore if s.startswith(full_url.replace("http://", "").replace("https://", "").replace(site_url, "")) == full_url]

		count += 1

		# The next line of code skips indexing namespaces excluded in robots.txt
		if len(in_matching_namespace) < 2:
			# lastmod = final_urls[full_url]

			# If URL is not relative internal link and does not start with http:// or https://
			# Used to make sure link uses the right format
			if not full_url.startswith("http://") and not full_url.startswith("https://") and not full_url.startswith("/"):
				log_error(full_url, "Not applicable", "URL does not begin with http:// or https://.", discovered_urls, broken_urls)

			if "//" in full_url.replace("https://", "").replace("http://", ""):
				log_error(full_url, "Not applicable", "URL contains double slash.", discovered_urls, broken_urls)

			if "/assets/" in full_url or ".pdf" in full_url:
				continue

			# if lastmod and os.path.isfile("search.db") == True:
			# 	try:
			# 		last_mod = datetime.datetime.strptime(lastmod, '%Y-%m-%dT%H:%M:%S+00:00')
			# 		# get last index time from index_stats.json
			# 		with open("index_stats.json", "r") as f:
			# 			index_stats = json.load(f)

			# 		last_index_time = index_stats["last_index_time"]

			# 		if last_mod < last_index_time:
			# 			# Don't index sites that were part of yesterday's index (indexes happen daily)
			# 			continue

			# 		if last_mod < datetime.datetime.now() - datetime.timedelta(days=1):
			# 			# Don't index sites that were part of yesterday's index (indexes happen daily)
			# 			continue
			# 	except:
			# 		pass

			session = requests.Session()
			session.max_redirects = 3

			try:
				# Check if page is the right content type before indexing
				page_test = session.head(full_url, headers=config.HEADERS)
			except requests.exceptions.Timeout:
				log_error(full_url, "Unknown", "URL timed out.", discovered_urls, broken_urls)
				continue
			except requests.exceptions.TooManyRedirects:
				log_error(full_url, "Unknown", "URL redirected too many times.", discovered_urls, broken_urls)
				continue
			except:
				log_error(full_url, "Unknown", "Error retrieving URL.", discovered_urls, broken_urls)
				continue

			# if text is html
			# if page_test.headers and page_test.headers.get("content-type") and "text/html" not in page_test.headers["content-type"] and "text/plain" in page_test.headers["content-type"]:
			# 	continue

			try:
				page = session.get(full_url, timeout=10, headers=config.HEADERS, allow_redirects=True)
			except requests.exceptions.Timeout:
				log_error(full_url, "Unknown", "URL timed out.", discovered_urls, broken_urls)
				continue
			except requests.exceptions.TooManyRedirects:
				log_error(full_url, "Unknown", "URL redirected too many times.", discovered_urls, broken_urls)
				continue
			except:
				log_error(full_url, "Unknown", "Unknown error processing URL.", discovered_urls, broken_urls)
				continue

			if page.status_code == 404:
				# is_in_db = cursor.execute("SELECT * FROM posts WHERE url = ?", (full_url,)).fetchall()
				message = "Page not found"

				log_error(full_url, page.status_code, message, discovered_urls, broken_urls)
				continue
			elif page.status_code == 301 or page.status_code == 302 or page.status_code == 308:
				# Handle temporary and permanent redirects

				# is_in_db = cursor.execute("SELECT * FROM posts WHERE url = ?", (full_url,)).fetchall()
				# if len(is_in_db) > 0:
				# 	cursor.execute("DELETE FROM posts WHERE url = ?;", (full_url,))

				redirected_to = page.headers["Location"]
				
				if redirected_to:
					final_urls[redirected_to] = ""

					iterate_list_of_urls.append(redirected_to)

					discovered_urls[redirected_to] = redirected_to
					
			elif page.status_code != 200:
				print("{} page failed to load.".format(full_url))
				message = "Page failed to load"

				log_error(full_url, page.status_code, message, discovered_urls, broken_urls)
				continue

			page_desc_soup = BeautifulSoup(page.content, "html5lib")

			if page_desc_soup.select("e-content"):
				page_text = page_desc_soup.select("e-content")[0]
			elif page_desc_soup.select("h-entry"):
				page_text = page_desc_soup.select("h-entry")
			elif page_desc_soup.find("main"):
				page_text = page_desc_soup.find("main")
			elif page_desc_soup.find("div", {"id": "main"}):
				page_text = page_desc_soup.find("div", {"id": "main"})
			elif page_desc_soup.find("div", {"id": "app"}):
				page_text = page_desc_soup.find("div", {"id": "app"})
			elif page_desc_soup.find("div", {"id": "page"}):
				page_text = page_desc_soup.find("div", {"id": "page"})
			elif page_desc_soup.find("div", {"id": "application-main"}):
				page_text = page_desc_soup.find("div", {"id": "application-main"})
			else:
				page_text = page_desc_soup.find("body")

			# Only index if noindex attribute is not present
			check_if_no_index = page_desc_soup.find("meta", {"name":"robots"})

			if check_if_no_index == None:
				check_if_no_index = ""
			else:
				check_if_no_index = check_if_no_index["content"]

			if page_text == None:
				log_error(full_url, page.status_code, "Page has no content (likely cannot be processed correctly).", discovered_urls, broken_urls)
				continue

			links = page_desc_soup.find_all("a")

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

			final_urls, iterate_list_of_urls, all_links, external_links = page_link_discovery(links, final_urls, iterate_list_of_urls, full_url, all_links, external_links, discovered_urls, site_url, count)

			# if "noindex" in check_if_no_index:
			# 	# Check if a page now marked as noindex is in the database
			# 	# If a page is marked as noindex and is in the database, we delete it from the database
				
			# 	is_in_db = cursor.execute("SELECT * FROM posts WHERE url = ?", (full_url,)).fetchall()
			# 	if len(is_in_db) > 0:
			# 		cursor.execute("DELETE FROM posts WHERE url = ?;", (full_url,))
			# 		continue

			page_text, page_desc_soup, published_on, meta_description, doc_title, category, important_phrases, remove_doc_title_from_h1_list, noindex = crawler.page_info.get_page_info(page_text, page_desc_soup, full_url, discovered_urls, broken_urls)

			if noindex == True:
				continue

			# images = page_desc_soup.find_all("img")

			#images_indexed = crawler.image_handling.crawl_images(images_indexed, published_on, cursor, full_url, discovered_urls, broken_urls, images, image_urls)

			#This will make sure we do not double count h1s that are classed as titles if no doc title is provided

			if remove_doc_title_from_h1_list == True:
				heading_info["h1"] = heading_info["h1"].remove(doc_title)
				
			try:
				pages_indexed = add_to_database(full_url, published_on, doc_title, meta_description, category, heading_info, page, important_phrases, pages_indexed, page_text, len(links))
			except Exception as e:
				log_error(full_url, page.status_code, e, discovered_urls, broken_urls)
				print("error with {}".format(full_url))
				print(e)
				logging.warning("error with {}".format(full_url))
				logging.warning(e)

		continue

	print('finished {}'.format(full_url))

	return pages_indexed, images_indexed, iterate_list_of_urls

def page_link_discovery(links, final_urls, iterate_list_of_urls, page_being_processed, all_links, external_links, discovered_urls, site_url, count):
	"""
		Finds all the links on the page and adds them to the list of links to crawl.
	"""

	for link in links:
		if link.get("href"):
			link["href"] = link["href"].split("?")[0]
			# // are external links so they should not be processed
			if link["href"].startswith("geo:") or link["href"].startswith("xmpp:") or link["href"].startswith("mailto:") or link["href"].startswith("javascript:") or link["href"].startswith("tel:") or link["href"].startswith("data:") or link["href"].startswith("ftp:") or link["href"].startswith("sms:"):
				continue
			if link["href"].startswith("//"):
				all_links.append([page_being_processed, link.get("href"), datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "external"])
				external_links["https://" + link["href"]] = page_being_processed
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
				
			# Don't index pages not on my site

			if "?" in full_link:
				full_link = full_link[:full_link.index("?")]

			if full_link.endswith("//"):
				full_link = full_link[:-1]

			if "mailto:" in full_link or "ftp:" in full_link or "gemini:" in full_link:
				continue

			if "./" in full_link:
				full_link = full_link.replace("./", "")

			# site_url not in full_link and
			# if "#" not in full_link or ".xml" not in full_link or not full_link.startswith("mailto:"):
			# 	all_links.append([page_being_processed, link.get("href"), datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "external"])
			# 	external_links[link["href"]] = page_being_processed
			# 	continue

			# Only add URLs to indexing list that are not: excluded, contain #, start with an excluded term, already in list of urls to crawl
			# and (full_link.startswith("https://jamesg.blog") or full_link.startswith("http://jamesg.blog")) \

			if full_link not in final_urls.keys() \
			and "#" not in full_link \
			and (full_link.startswith("https://{}".format(site_url)) or full_link.startswith("http://{}".format(site_url))) \
			and ".xml" not in full_link \
			and ".pdf" not in full_link \
			and not full_link.startswith("//") \
			and not ".jpeg" in full_link and not ".png" in full_link and not ".jpg" in full_link and not ".gif" in full_link \
			and not full_link.startswith("mailto:") \
			and len(final_urls) < 1000:
			# and ((reindex == True and len(page_being_processed.replace("https://").strip("/").split("/")) == 0) or reindex == False):
				all_links.append([page_being_processed, link.get("href"), datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "internal", link.text])
				print("indexing queue now contains " + full_link)
				final_urls[full_link] = ""

				iterate_list_of_urls.append(full_link)

				discovered_urls[full_link] = page_being_processed

	return final_urls, iterate_list_of_urls, all_links, external_links