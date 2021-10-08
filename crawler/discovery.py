import datetime
import logging

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

			# make sure urls with // are processed correctly
			# example: https://www.test.com//text.html should become https://www.test.com/text.html
			if "//" in full_link.replace("://", ""):
				if full_link.startswith("http://"):
					protocol = "http://"
				elif full_link.startswith("https://"):
					protocol = "https://"

				url = full_link.replace("http://", "").replace("https://", "").replace("//", "/")

				full_link = protocol + url

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