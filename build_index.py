from bs4 import BeautifulSoup
import requests
import datetime
import logging
from config import ROOT_DIRECTORY
import json
import csv
import os
import config
import crawler.url_handling as url_handling
import concurrent.futures

# ignore warning about http:// connections
from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

start_time = datetime.datetime.now()

# initialize folders before logging starts to prevent an error on first run

def initialize_folders():
	dirs_to_make = ["logs", "static/images", "charts"]

	for d in dirs_to_make:
		try:
			os.mkdir(d)
		except:
			print("{} already created. Skipping creation.".format(d))

	files_to_create = ["static/index_stats.csv", "static/all_links.csv", "static/external_link_status.csv", "data/all_links.csv"]

	header_rows_to_write = [
		"total_pages_indexed,total_images_indexed,pages_indexed_in_last_crawl,images_indexed_in_last_crawl,html_content_length,last_index_start,last_index_end,crawl_duration,external_links_found",
		"page_linking,link_to,datetime,link_type",
		"url,status_code,domain_name,date",
		"page_linking,link_to,datetime,link_type",
	]

	for f in range(0, len(files_to_create)):
		with open(ROOT_DIRECTORY + "/" + files_to_create[f], "a") as file:
			writer = csv.writer(file)

			writer.writerow(header_rows_to_write[f])

logging.basicConfig(level=logging.DEBUG, filename="{}/logs/{}.log".format(ROOT_DIRECTORY, datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

broken_urls = []

external_links = {}

links = []

# Dict to track newly discovered urls
# Key = URL discovered
# Value = Page to process

discovered_urls = {}

def find_robots_directives(site_url):
	"""
		Finds the robots.txt file on a website, reads the contents, then follows directives.
	"""

	# allow five redirects before raising an exception
	session = requests.Session()
	session.max_redirects = 5
	
	try:
		read_robots = session.get("https://{}/robots.txt".format(site_url), headers=config.HEADERS, timeout=5, allow_redirects=True, verify=False)
	except requests.exceptions.RequestException as e:
		logging.error("Error with site: {}".format(e))
		return [], []
	except requests.exceptions.ConnectionError:
		logging.error("Connection error with site: {}".format(site_url))
		return [], []
	except:
		print("Error: Could not find robots.txt file on {}".format(site_url))
		logging.error("Error: Could not find robots.txt file on {}".format(site_url))
		return [], []

	if read_robots.status_code == 404:
		logging.warning("Robots.txt not found on {}".format(site_url))
		return [], ["https://{}/sitemap.xml".format(site_url)]

	namespaces_to_ignore = []
	
	next_line_is_to_be_read = False
	
	sitemap_urls = []

	for processed_line in read_robots.content.decode("utf-8").split("\n"):
		# Only read directives pointed at all user agents or my crawler user agent
		if "User-agent: *" in processed_line or "User-agent: jamesg-search" in processed_line:
			next_line_is_to_be_read = True

		if "Disallow:" in processed_line and next_line_is_to_be_read == True:
			if processed_line == "Disallow: /*" or processed_line == "Disallow: *":
				print("All URLs disallowed. Crawl complete")
				return namespaces_to_ignore, sitemap_urls
			namespaces_to_ignore.append(processed_line.split(":")[1].strip())
		elif "Sitemap:" in processed_line and next_line_is_to_be_read == True:
			# Second : will be in the URL of the sitemap so it needs to be preserved
			sitemap_url = processed_line.split(":")[1] + ":" + processed_line.split(":")[2]
			sitemap_urls.append(sitemap_url.strip())
		elif len(processed_line) == 0:
			next_line_is_to_be_read = False

	if sitemap_urls == []:
		sitemap_urls.append("https://{}/sitemap.xml".format(site_url))

	return namespaces_to_ignore, sitemap_urls

def process_domain(site, reindex):
	final_urls = {}
	
	namespaces_to_ignore, sitemap_urls = find_robots_directives(site)

	if namespaces_to_ignore == "broken":
		return 0, [], site

	# Parse sitemap indexes
	for u in sitemap_urls:
		r = requests.get(u, verify=False, headers=config.HEADERS, timeout=5, allow_redirects=True)
		if r.status_code == 200:
			# parse with bs4
			soup = BeautifulSoup(r.text, "html.parser")
			if soup.find("sitemapindex"):
				# find all the urls
				all_sitemaps = soup.find_all("loc")
				for sitemap in all_sitemaps:
					sitemap_urls.append(sitemap.text)
					print("will crawl URLs in {} sitemap".format(sitemap.text))
					logging.debug("will crawl URLs in {} sitemap".format(sitemap.text))
			else:
				print("will crawl URLs in {} sitemap".format(u))
				logging.debug("will crawl URLs in {} sitemap".format(u))

	sitemap_urls = list(set(sitemap_urls))

	# Added just to make sure the homepage is in the initial crawl queue
	if len(sitemap_urls) > 2:
		final_urls["https://{}".format(site)] = ""

	for s in sitemap_urls:
		# Only URLs not already discovered will be added by this code
		# Lastmod dates will be added to the final_url value related to the URL if a lastmod date is available
		feed = requests.get(s, headers=config.HEADERS, timeout=5, verify=False, allow_redirects=True)

		soup = BeautifulSoup(feed.content, "lxml")

		urls = list(soup.find_all("url"))

		for u in urls:
			if "/tag/" in u.find("loc").text:
				continue
			if u.find("lastmod"):
				final_urls[u.find("loc").text] = u.find("lastmod").text
			else:
				final_urls[u.find("loc").text] = ""

	if reindex == True:
		return 100, final_urls, namespaces_to_ignore
	else:
		return 2, final_urls, namespaces_to_ignore

def build_index(site, reindex=False):
	# remove from queue before indexing starts
	# prevents against failure to index and not being recognised in file
	with open("crawl_queue.txt", "r") as f:
		rows = f.readlines()

	# if site in rows:
	# 	rows.remove(site)
	
	# if site + "\n" in rows:
	# 	rows.remove(site  + "\n")

	# with open("crawl_queue.txt", "w+") as f:
	# 	f.writelines(rows)

	headers = {
		"Authorization": config.ELASTICSEARCH_API_TOKEN
	}

	r = requests.post("https://es-indieweb-search.jamesg.blog/feeds", headers=headers, data={"website_url": site})

	if r.status_code == 200 and not r.json()["message"]:
		print("feeds retrieved for {}".format(site))
		logging.debug("feeds retrieved for {}".format(site))
		feeds = r.json()
	elif r.status_code == 200 and r.json()["message"]:
		print("Result from URL request to /feeds endpoint on elasticsearch server: {}".format(r.json()["message"]))
		logging.debug("Result from URL request to /feeds endpoint on elasticsearch server: {}".format(r.json()["message"]))
		feeds = []
	else:
		print("ERROR: feeds not retrieved for {} (status code {})".format(site, r.status_code))
		logging.error("feeds not retrieved for {} (status code {})".format(site, r.status_code))
		feeds = []

	if feeds:
		feed_urls = [item.get("url") for item in feeds]
	else:
		feed_urls = []

	# get date
	date = datetime.datetime.now().strftime("%Y-%m-%d")

	with open("crawled.csv", "a+") as f:
		csv.writer(f).writerow([site, date])

	# read crawl_queue.txt
	crawl_budget, final_urls, namespaces_to_ignore = process_domain(site, reindex)

	if crawl_budget == 0:
		return site, []

	if len(final_urls) == 0:
		final_urls["https://{}".format(site)] = ""

	iterate_list_of_urls = list(final_urls.keys())

	try:
		requests.get("https://" + site, headers=config.HEADERS, timeout=5, allow_redirects=True, verify=False)
	except Exception as e:
		print(e)
		print("error with {} url and site, skipping".format(iterate_list_of_urls[0]))
		logging.debug("error with {} url and site, skipping".format(iterate_list_of_urls[0]))
		return

	print("processing {}".format(site))
	logging.debug("processing {}".format(site))

	indexed = 0
	valid_count = 0	

	indexed_list = {}

	print("crawl budget: {}".format(crawl_budget))

	print("{} urls part of initial crawl".format(len(iterate_list_of_urls)))

	all_feeds = []
	discovered_feeds_dict = {}
	
	for url in iterate_list_of_urls:
		url_indexed, discovered, valid, discovered_feeds = url_handling.crawl_urls(final_urls, namespaces_to_ignore, indexed, links, external_links, discovered_urls, iterate_list_of_urls, site, crawl_budget, url, [], feed_urls, site, True)

		if valid == True:
			valid_count += 1

		if valid_count == 0 and indexed == 25:
			break
		
		indexed += 1

		print("{}/{}".format(indexed, crawl_budget))
		logging.debug("{} - {}/{}".format(site, indexed, crawl_budget))

		if indexed > crawl_budget:
			break

		indexed_list[url_indexed] = True

		for f in discovered_feeds:
			if discovered_feeds_dict.get(f.get("url")) == None:
				all_feeds.append(f)
				feed_urls.append(f.get("url"))
				discovered_feeds_dict[f.get("url")] = True

	# update database to list new feeds

	headers["Content-Type"] = "application/json"

	r = requests.post("https://es-indieweb-search.jamesg.blog/save", json={"feeds": all_feeds}, headers=headers)

	print(all_feeds)

	if r.status_code == 200:
		print("feeds updated in database for {}".format(site))
		logging.debug("feeds updated database for {}".format(site))
	else:
		print("ERROR: feeds not updated for {} (status code {})".format(site, r.status_code))
		logging.error("feeds not updated for {} (status code {})".format(site, r.status_code))

	# write to crawled.csv
	with open("crawled.csv", "a+") as f:
		csv.writer(f).writerow([site, date])

	for item in discovered.keys():
		if not indexed_list.get(item):
			print("{} not indexed, added".format(item))
			iterate_list_of_urls.append(item)

	return url_indexed, discovered

if __name__ == "__main__":
	futures = []

	sites_indexed = 0

	with open("crawl_queue.txt", "r") as f:
		to_crawl = f.readlines()

	# don't include items on block list in a crawl
	# used to avoid accidentally crawling sites that have already been flagged as spam
	with open("blocklist.txt", "r") as block_file:
		block_list = block_file.readlines()

	to_crawl = [item for item in to_crawl if item not in block_list]

	with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
		futures = [executor.submit(build_index, url.replace("\n", "")) for url in to_crawl]
		
		while len(futures) > 0:
			for future in concurrent.futures.as_completed(futures):
				sites_indexed += 1

				print("SITES INDEXED: {}".format(sites_indexed))
				logging.info("SITES INDEXED: {}".format(sites_indexed))

				try:
					url_indexed, discovered = future.result()

					if url_indexed == None:
						futures = []
						break
				except Exception as e:
					print(e)
					print("Skipped indexing site any more due to error.")
					pass

				futures.remove(future)