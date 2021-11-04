import requests
import datetime
import logging
import concurrent.futures
import cProfile
import mf2py
import config
from bs4 import BeautifulSoup
from config import ROOT_DIRECTORY
import crawler.url_handling as url_handling

# ignore warning about http:// connections
from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

start_time = datetime.datetime.now()

logging.basicConfig(
	level=logging.DEBUG, 
	filename="{}/logs/{}.log".format(ROOT_DIRECTORY, datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
	datefmt='%Y-%m-%d %H:%M:%S'
)

print("Printing logs to {}/logs/{}.log".format(ROOT_DIRECTORY, datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

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

	protocol = "https://"

	try:
		r = requests.get("https://" + site_url, headers=config.HEADERS, timeout=5, allow_redirects=True, verify=False)
	except Exception as e:
		logging.debug(e)
		pass

	try:
		r = requests.get("http://" + site_url, headers=config.HEADERS, timeout=5, allow_redirects=True, verify=False)
		protocol = "http://"
	except:
		logging.debug(e)
		logging.debug("error with {} url and site, skipping".format(site_url))
		return

	# get accept header
	accept = r.headers.get("accept")

	if accept:
		headers = config.HEADERS
		headers["accept"] = accept.split(",")[0]

	# allow five redirects before raising an exception
	session = requests.Session()
	session.max_redirects = 5
	
	try:
		read_robots = session.get("{}{}/robots.txt".format(protocol, site_url), headers=config.HEADERS, timeout=5, allow_redirects=True, verify=False)
	except requests.exceptions.RequestException as e:
		logging.error("Error with site: {}".format(e))
		return [], [], protocol
	except requests.exceptions.ConnectionError:
		logging.error("Connection error with site: {}".format(site_url))
		return [], [], protocol
	except:
		# "Error: Could not find robots.txt file on {}".format(site_url))
		logging.error("Error: Could not find robots.txt file on {}".format(site_url))
		return [], [], protocol

	if read_robots.status_code == 404:
		logging.warning("Robots.txt not found on {}".format(site_url))
		return [], ["{}{}/sitemap.xml".format(protocol, site_url)], protocol

	namespaces_to_ignore = []
	
	next_line_is_to_be_read = False
	
	sitemap_urls = []

	for processed_line in read_robots.content.decode("utf-8").split("\n"):
		# Only read directives pointed at all user agents or my crawler user agent
		if "User-agent: *" in processed_line or "User-agent: indieweb-search" in processed_line:
			next_line_is_to_be_read = True

		if "Disallow:" in processed_line and next_line_is_to_be_read == True:
			if processed_line == "Disallow: /*" or processed_line == "Disallow: *":
				# print("All URLs disallowed. Crawl complete")
				return namespaces_to_ignore, sitemap_urls, protocol
			namespaces_to_ignore.append(processed_line.split(":")[1].strip())
		elif "Sitemap:" in processed_line and next_line_is_to_be_read == True:
			# Second : will be in the URL of the sitemap so it needs to be preserved
			sitemap_url = processed_line.split(":")[1] + ":" + processed_line.split(":")[2]
			sitemap_urls.append(sitemap_url.strip())
		elif len(processed_line) == 0:
			next_line_is_to_be_read = False

	if sitemap_urls == []:
		sitemap_urls.append("https://{}/sitemap.xml".format(site_url))

	return namespaces_to_ignore, sitemap_urls, protocol

def process_domain(site, reindex):
	"""
		Processes a domain and executes a function that crawls all pages on the domain.
		This function keeps track of URLs that have been crawled, the hashes of pages that have been crawled
		and other key information required to manage a site crawl.
	"""
	final_urls = {}
	
	namespaces_to_ignore, sitemap_urls, protocol = find_robots_directives(site)

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
					# print("will crawl URLs in {} sitemap".format(sitemap.text))
					logging.debug("will crawl URLs in {} sitemap".format(sitemap.text))
			else:
				# print("will crawl URLs in {} sitemap".format(u))
				logging.debug("will crawl URLs in {} sitemap".format(u))

	sitemap_urls = list(set(sitemap_urls))

	# Added just to make sure the homepage is in the initial crawl queue
	if len(sitemap_urls) > 2:
		final_urls["http://{}".format(site)] = ""

	for s in sitemap_urls:
		# Only URLs not already discovered will be added by this code
		# Lastmod dates will be added to the final_url value related to the URL if a lastmod date is available
		feed = requests.get(s, headers=config.HEADERS, timeout=5, verify=False, allow_redirects=True)

		soup = BeautifulSoup(feed.content, "lxml")

		urls = list(soup.find_all("url"))

		headers = {
			"Authorization": config.ELASTICSEARCH_API_TOKEN
		}

		r = requests.post(
			"https://es-indieweb-search.jamesg.blog/create_sitemap", 
			data={"sitemap_url": s, "domain": site}, 
			headers=headers
		)

		if r.status_code == 200:
			# print(r.text)
			# print("sitemaps added to database for {}".format(site))
			logging.debug("sitemaps added to database for {}".format(site))
		else:
			# print("ERROR: sitemap not added for {} (status code {})".format(site, r.status_code))
			logging.error("sitemap not added for {} (status code {})".format(site, r.status_code))

		for u in urls:
			if "/tag/" in u.find("loc").text:
				continue
			if u.find("lastmod"):
				final_urls[u.find("loc").text] = u.find("lastmod").text
			else:
				final_urls[u.find("loc").text] = ""

	if reindex == True:
		return 100, final_urls, namespaces_to_ignore, protocol
	else:
		# crawl budget is now 15,000
		return 15000, final_urls, namespaces_to_ignore, protocol

def build_index(site, reindex=False):
	# do not index IPs
	# sites must have a domain name to qualify for inclusion in the index
	if site.replace(".", "").isdigit():
		return site, []

	headers = {
		"Authorization": config.ELASTICSEARCH_API_TOKEN
	}

	r = requests.post("https://es-indieweb-search.jamesg.blog/feeds", headers=headers, data={"website_url": site})

	if r.status_code == 200 and r.json() and not r.json().get("message"):
		# print("feeds retrieved for {}".format(site))
		logging.debug("feeds retrieved for {}".format(site))
		feeds = r.json()
	elif r.status_code == 200 and r.json() and r.json().get("message"):
		# print("Result from URL request to /feeds endpoint on elasticsearch server: {}".format(r.json()["message"]))
		logging.debug("Result from URL request to /feeds endpoint on elasticsearch server: {}".format(r.json()["message"]))
		feeds = []
	elif r.status_code == 200 and not r.json():
		# print("No feeds retrieved for {} but still 200 response".format(site))
		logging.debug("No feeds retrieved for {} but still 200 response".format(site))
		feeds = []
	else:
		# print("ERROR: feeds not retrieved for {} (status code {})".format(site, r.status_code))
		logging.error("feeds not retrieved for {} (status code {})".format(site, r.status_code))
		feeds = []

	feed_urls = feeds

	# read crawl_queue.txt
	crawl_budget, final_urls, namespaces_to_ignore, protocol = process_domain(site, reindex)

	if crawl_budget == 0:
		return site, []

	if len(final_urls) == 0:
		final_urls["{}{}".format(protocol, site)] = ""

	iterate_list_of_urls = list(final_urls.keys())

	print("processing {}".format(site))
	logging.debug("processing {}".format(site))

	indexed = 0
	valid_count = 0	

	indexed_list = {}

	logging.debug("crawl budget: {}".format(crawl_budget))

	logging.debug("{} urls part of initial crawl".format(len(iterate_list_of_urls)))

	all_feeds = []
	discovered_feeds_dict = {}

	try:
		h_card = mf2py.Parser(protocol + site, timeout=5, verify=False)
	except:
		h_card = []
		logging.debug("no h-card could be found on {} home page".format(site))

	session = requests.Session()

	web_page_hashes = {}

	crawl_depths = {}

	average_crawl_speed = []

	homepage_meta_description = ""

	crawl_budget = 20
	
	for url in iterate_list_of_urls:
		if crawl_depths.get("url"):
			crawl_depth = crawl_depths.get("url")
			if crawl_depth > 5:
				# print("crawl depth for {} is {}".format(url, crawl_depth))
				logging.debug("crawl depth for {} is {}".format(url, crawl_depth))
		else:
			crawl_depth = 0

		if indexed_list.get(url):
			continue

		url_indexed, discovered, valid, discovered_feeds, web_page_hash, crawl_depth, average_crawl_speed = url_handling.crawl_urls(final_urls, namespaces_to_ignore, indexed, links, external_links, discovered_urls, iterate_list_of_urls, site, crawl_budget, url, [], feed_urls, site, session, web_page_hashes, average_crawl_speed, homepage_meta_description, True, h_card, crawl_depth)

		if valid == True:
			valid_count += 1

		if web_page_hash != None:
			web_page_hashes[web_page_hash] = url
	
		average_crawl_speed.extend(average_crawl_speed)

		if len(average_crawl_speed) > 100:
			average_crawl_speed = average_crawl_speed[:100]

		if average_crawl_speed and len(average_crawl_speed) and (len(average_crawl_speed) / len(average_crawl_speed) > 4):
			logging.debug("average crawl speed is {}, stopping crawl".format(len(average_crawl_speed) / len(average_crawl_speed)))
			with open("failed.txt", "a") as f:
				f.write("{} average crawl speed is {}, stopping crawl \n".format(site, len(average_crawl_speed) / len(average_crawl_speed)))

			iterate_list_of_urls = []
		
		indexed += 1

		logging.debug("{}/{}".format(indexed, crawl_budget))
		logging.debug("{} - {}/{}".format(site, indexed, crawl_budget))

		if indexed > crawl_budget:
			break

		indexed_list[url_indexed] = True
		web_page_hashes[web_page_hash] = url

		for f in discovered_feeds:
			if discovered_feeds_dict.get(f.get("feed_url")) == None:
				all_feeds.append(f)
				feed_urls.append(f.get("feed_url"))
				discovered_feeds_dict[f.get("feed_url")] = True

		for key, value in discovered.items():
			if not indexed_list.get(key):
				logging.debug("{} not indexed, added".format(key))
				iterate_list_of_urls.append(key)

			crawl_depths[key] = value

	# update database to list new feeds

	headers["Content-Type"] = "application/json"

	# exclude wordpress json feeds for now
	# only save first 25 feeds
	feeds = [f for f in all_feeds[:25] if "wp-json" not in f]

	r = requests.post("https://es-indieweb-search.jamesg.blog/save", json={"feeds": all_feeds}, headers=headers)

	if r.status_code == 200:
		# print("feeds updated in database for {}".format(site))
		logging.debug("feeds updated database for {}".format(site))
	else:
		# print("ERROR: feeds not updated for {} (status code {})".format(site, r.status_code))
		logging.error("feeds not updated for {} (status code {})".format(site, r.status_code))

	del headers["Content-Type"]

	r = requests.post("https://es-indieweb-search.jamesg.blog/create_crawled", data={"url": site}, headers=headers)

	if r.status_code == 200:
		# print(r.text)
		# print("crawl recorded in database for {}".format(site))
		logging.debug("crawl recorded in database for {}".format(site))
	else:
		# print("ERROR: crawl not recorded in database for {} (status code {})".format(site, r.status_code))
		logging.error("crawl not recorded in database for {} (status code {})".format(site, r.status_code))
			
	with open("crawl_queue.txt", "r") as f:
		rows = f.readlines()

	if site in rows:
		rows.remove(site)
	
	if site + "\n" in rows:
		rows.remove(site + "\n")

	with open("crawl_queue.txt", "w+") as f:
		f.writelines(rows)

	return url_indexed, discovered

def main():
	futures = []

	sites_indexed = 0

	with open("crawl_queue.txt", "r") as f:
		to_crawl = f.readlines()

	# don't include items on block list in a crawl
	# used to avoid accidentally crawling sites that have already been flagged as spam
	with open("blocklist.txt", "r") as block_file:
		block_list = block_file.readlines()

	to_crawl = [item.lower() for item in to_crawl if item not in block_list]

	with concurrent.futures.ThreadPoolExecutor() as executor:
		futures = [executor.submit(build_index, url.replace("\n", "")) for url in to_crawl]
		
		while len(futures) > 0:
			for future in concurrent.futures.as_completed(futures):
				sites_indexed += 1

				print("SITES INDEXED: {}".format(sites_indexed))
				logging.info("SITES INDEXED: {}".format(sites_indexed))

				try:
					url_indexed, _ = future.result()

					if url_indexed == None:
						futures = []
						break
				except Exception as e:
					# print(e)
					# print("Skipped indexing site any more due to error.")
					pass

				futures.remove(future)

if __name__ == "__main__":
	# cProfile.run("main()", "profile.txt")
	main()