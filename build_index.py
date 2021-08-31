from bs4 import BeautifulSoup
import requests
import datetime
import sqlite3
import logging
from config import ROOT_DIRECTORY
import json
import csv
import os

from shutil import copyfile

import config

from crawler import url_handling, test_queries, create_charts

start_time = datetime.datetime.now()

# initialize folders before logging starts to prevent an error on first run

def initialize_folders():
	dirs_to_make = ["logs", "static/images", "charts"]

	for d in dirs_to_make:
		try:
			os.mkdir(d)
		except:
			print("{} already created. Skipping creation.".format(d))

	files_to_create = ["static/index_stats.csv", "static/all_links.csv", "static/external_link_status.csv"]

	header_rows_to_write = [
		"total_pages_indexed,total_images_indexed,pages_indexed_in_last_crawl,images_indexed_in_last_crawl,html_content_length,last_index_start,last_index_end,crawl_duration,external_links_found",
		"page_linking,link_to,datetime,link_type",
		"url,status_code,domain_name,date"
	]

	for f in range(0, len(files_to_create)):
		with open(ROOT_DIRECTORY + "/" + files_to_create[f], "a") as file:
			writer = csv.writer(file)

			writer.writerow(header_rows_to_write[f])

initialize_folders()

logging.basicConfig(level=logging.DEBUG, filename="{}/logs/{}.log".format(ROOT_DIRECTORY, datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

broken_urls = []

external_links = {}

links = []

# Dict to track newly discovered urls
# Key = URL discovered
# Value = Page to process

discovered_urls = {}
<<<<<<< HEAD

def find_robots_directives(site_url):
	"""
		Finds the robots.txt file on a website, reads the contents, then follows directives.
	"""
	read_robots = requests.get("https://{}/robots.txt".format(site_url), headers=config.HEADERS)

	if read_robots.status_code == 404:
		logging.warning("Robots.txt not found on {}".format(site_url))
		url_handling.log_error("https://{}/robots.txt".format(site_url), read_robots.status_code, "Site is missing a robots.txt file.", discovered_urls, broken_urls)

		return [], ["https://{}/sitemap.xml".format(site_url)]
=======
			
def find_robots_directives(cursor):
	"""
		Finds the robots.txt file on a website, reads the contents, then follows directives.
	"""
	read_robots = requests.get("https://{}/robots.txt".format(config.SITE_URL), headers=config.HEADERS)

	if read_robots.status_code == 404:
		logging.warning("Robots.txt not found on {}".format(config.SITE_URL))
		url_handling.log_error("https://{}/robots.txt".format(config.SITE_URL), read_robots.status_code, "Site is missing a robots.txt file.", discovered_urls, broken_urls)

		return [], ["https://{}/sitemap.xml".format(config.SITE_URL)]
>>>>>>> c0e980441926b4504939b2fa460fb12f98d9e325

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
<<<<<<< HEAD
		sitemap_urls.append("https://{}/sitemap.xml".format(site_url))
=======
		sitemap_urls.append("https://{}/sitemap.xml".format(config.SITE_URL))
>>>>>>> c0e980441926b4504939b2fa460fb12f98d9e325

	return namespaces_to_ignore, sitemap_urls

def log_contents(cursor, pages_indexed, images_indexed):
	get_total_posts_indexed = cursor.execute("SELECT COUNT(url) FROM posts;").fetchone()[0]
	get_total_images_indexed = cursor.execute("SELECT COUNT(post_url) FROM images;").fetchone()[0]

	content_length = cursor.execute("SELECT SUM(length) FROM posts;").fetchone()[0]

	end_time = datetime.datetime.now()

	# Save most recent crawl to a JSON file so I can show the data
	with open(ROOT_DIRECTORY + "/static/index_stats.json", "w+") as file:
		data_to_save = {
			"total_pages_indexed": get_total_posts_indexed,
			"total_images_indexed": get_total_images_indexed,
			"pages_indexed_in_last_crawl": pages_indexed,
			"images_indexed_in_last_crawl": images_indexed,
			"html_content_length": content_length,
			"last_index_start": start_time.strftime("%Y-%m-%d %H:%M:%S"),
			"last_index_end": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
			"crawl_duration": "{}".format(end_time - start_time),
			"external_links_found": len(external_links),
			"errors_found": len(broken_urls)
		}

		json.dump(data_to_save, file, ensure_ascii=False, indent=4)

	# Keep record of all crawls
	with open(ROOT_DIRECTORY + "/data/index_stats.csv", "a") as file:
		data_to_save = [get_total_posts_indexed, get_total_images_indexed, pages_indexed, images_indexed, content_length, start_time.strftime("%Y-%m-%d %H:%M:%S"), datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"{}".format(end_time - start_time), len(external_links)]
		
		writer = csv.writer(file)

		writer.writerows([data_to_save])

	# Save all broken urls to db table

	now = datetime.datetime.now().strftime("%Y-%m-%d-%H:%M:%S")

	# with open(ROOT_DIRECTORY + "/static/index_status.json", "w+") as index_status_main:
	# 	json.dump(broken_urls, index_status_main, ensure_ascii=False, indent=4)

	# Delete all outstanding crawl errors before populating new ones
<<<<<<< HEAD
	# cursor.execute("DELETE FROM crawl_errors;")

	# for item in broken_urls:
	# 	try:
	# 		cursor.execute("INSERT INTO crawl_errors VALUES(?, ?, ?, ?, ?);", (item["url"], item["status_code"], item["message"], item["discovered"], now, ))
	# 	except:
	# 		print("error processing {}".format(item))
	# 		continue

	# with open(ROOT_DIRECTORY + "/logs/{}-index_status.json".format(now), "w+") as index_status_file:
	# 	json.dump(broken_urls, index_status_file, ensure_ascii=False, indent=4)
=======
	cursor.execute("DELETE FROM crawl_errors;")

	for item in broken_urls:
		try:
			cursor.execute("INSERT INTO crawl_errors VALUES(?, ?, ?, ?, ?);", (item["url"], item["status_code"], item["message"], item["discovered"], now, ))
		except:
			print("error processing {}".format(item))

	with open(ROOT_DIRECTORY + "/logs/{}-index_status.json".format(now), "w+") as index_status_file:
		json.dump(broken_urls, index_status_file, ensure_ascii=False, indent=4)
>>>>>>> c0e980441926b4504939b2fa460fb12f98d9e325

	os.replace("new_search.db", "search.db")

	# Send notification if there are crawl errors

	if len(broken_urls) > 0:
		message = "{} errors found in crawl.".format(len(broken_urls))
		
		r = requests.post("https://maker.ifttt.com/trigger/crawl_issue/with/key/b4G5wb1JQabRPiRET9sq5l", data={"value1": message})

	print("Indexing complete.")
	logging.debug("Indexing complete.")

def build_index():
<<<<<<< HEAD
	# read crawl_queue.txt
	while True:
		# read crawl_queue.txt
		with open("crawl_queue.txt", "r") as file:
			file = file.readlines()
			site = file[0].strip()
		
		if os.path.isfile("search.db") == True:
			copyfile("search.db", "new_search.db")

		connection = sqlite3.connect("new_search.db", check_same_thread=False)

		with connection:
			cursor = connection.cursor()

			final_urls = {}

			# Create new tables if index does not already exist

			# if not os.path.isfile("search.db"):
			# 	print("please run 'flask seed build-tables' before attempting to build the index.")
			# else:
			# 	# Add URLs already discovered to the indexing queue
			# 	already_discovered_urls = cursor.execute("SELECT url FROM posts WHERE URL LIKE ? OR url LIKE ?", ("https://{}%".format(config.SITE_URL),"http://{}%".format(config.SITE_URL),)).fetchall()

			# 	if already_discovered_urls:
			# 		for u in already_discovered_urls:
			# 			final_urls[u[0]] = ""

			# Delete all old sitemaps and start from scratch
			# This is key because sometimes sitemaps change and I don't want to retrieve old ones
			# cursor.execute("DELETE FROM sitemaps;")
			
			namespaces_to_ignore, sitemap_urls = find_robots_directives(site)

			# Parse sitemap indexes
			for u in sitemap_urls:
				r = requests.get(u)
				if r.status_code == 200:
					# parse with bs4
					soup = BeautifulSoup(r.text, "html.parser")
					if soup.find("sitemapindex"):
						# find all the urls
						all_sitemaps = soup.find_all("loc")
						for sitemap in all_sitemaps:
							sitemap_urls.append(sitemap.text)
							cursor.execute("INSERT INTO sitemaps VALUES (?)", (sitemap.text, ))
							print("will crawl URLs in {} sitemap".format(sitemap.text))
					else:
						cursor.execute("INSERT INTO sitemaps VALUES (?)", (u, ))
						print("will crawl URLs in {} sitemap, added sitemap to database".format(u))
				elif r.status_code == 404:
					url_handling.log_error(u, r.status_code, "{} sitemap returns a 404 error.".format(u), discovered_urls, broken_urls)

			sitemap_urls = list(set(sitemap_urls))

			for s in sitemap_urls:
				# Only URLs not already discovered will be added by this code
				# Lastmod dates will be added to the final_url value related to the URL if a lastmod date is available
				feed = requests.get(s, headers=config.HEADERS)

				soup = BeautifulSoup(feed.content, "lxml")

				urls = list(soup.find_all("url"))

				for u in urls:
					if u.find("lastmod"):
						final_urls[u.find("loc").text] = u.find("lastmod").text
					else:
						final_urls[u.find("loc").text] = ""

			image_urls = []

			if len(final_urls) == 0:
				final_urls["https://{}".format(site)] = ""

			pages_indexed = 0
			images_indexed = 0

			iterate_list_of_urls = list(final_urls.keys())

			print(final_urls)

			pages_indexed, images_indexed, all_links, iterate_list_of_urls = url_handling.crawl_urls(final_urls, namespaces_to_ignore, cursor, pages_indexed, images_indexed, image_urls, links, external_links, discovered_urls, broken_urls, iterate_list_of_urls, site)

			log_contents(cursor, pages_indexed, images_indexed)

			with open("crawl_queue.txt", "r") as f:
				rows = f.readlines()[1:]

			with open("crawl_queue.txt", "w+") as f:
				for r in rows:
					f.write(r + "\n")

			with open(ROOT_DIRECTORY + "/data/all_links.csv","w") as f:
				wr = csv.writer(f)
				wr.writerow(["page_linking", "link_to", "datetime", "link_type", "anchor_text"])
				wr.writerows(all_links)

		#broken_links.check_for_invalid_links()

build_index()
=======
	if os.path.isfile("search.db") == True:
		copyfile("search.db", "new_search.db")

	connection = sqlite3.connect("new_search.db", check_same_thread=False)

	with connection:
		cursor = connection.cursor()

		final_urls = {}

		# Create new tables if index does not already exist

		if not os.path.isfile("search.db"):
			print("please run 'flask seed build-tables' before attempting to build the index.")
		else:
			# Add URLs already discovered to the indexing queue
			already_discovered_urls = cursor.execute("SELECT url FROM posts WHERE URL LIKE ? OR url LIKE ?", ("https://{}%".format(config.SITE_URL),"http://{}%".format(config.SITE_URL),)).fetchall()

			if already_discovered_urls:
				for u in already_discovered_urls:
					final_urls[u[0]] = ""

		# Delete all old sitemaps and start from scratch
		# This is key because sometimes sitemaps change and I don't want to retrieve old ones
		cursor.execute("DELETE FROM sitemaps;")

		namespaces_to_ignore, sitemap_urls = find_robots_directives(cursor)

		# Parse sitemap indexes
		for u in sitemap_urls:
			r = requests.get(u)
			if r.status_code == 200:
				# parse with bs4
				soup = BeautifulSoup(r.text, "html.parser")
				if soup.find("sitemapindex"):
					# find all the urls
					all_sitemaps = soup.find_all("loc")
					for sitemap in all_sitemaps:
						sitemap_urls.append(sitemap.text)
						cursor.execute("INSERT INTO sitemaps VALUES (?)", (sitemap.text, ))
						print("will crawl URLs in {} sitemap".format(sitemap.text))
				else:
					cursor.execute("INSERT INTO sitemaps VALUES (?)", (u, ))
					print("will crawl URLs in {} sitemap, added sitemap to database".format(u))
			elif r.status_code == 404:
				url_handling.log_error(u, r.status_code, "{} sitemap returns a 404 error.".format(u), discovered_urls, broken_urls)

		sitemap_urls = list(set(sitemap_urls))

		for s in sitemap_urls:
			# Only URLs not already discovered will be added by this code
			# Lastmod dates will be added to the final_url value related to the URL if a lastmod date is available
			feed = requests.get(s, headers=config.HEADERS)

			soup = BeautifulSoup(feed.content, "lxml")

			urls = list(soup.find_all("url"))

			for u in urls:
				if u.find("lastmod"):
					final_urls[u.find("loc").text] = u.find("lastmod").text
				else:
					final_urls[u.find("loc").text] = ""

		image_urls = []

		if len(final_urls) == 0:
			final_urls["https://{}".format(config.SITE_URL)] = ""

		pages_indexed = 0
		images_indexed = 0

		iterate_list_of_urls = list(final_urls.keys())

		iterate_list_of_urls = ["https://jamesg.blog/likes/"]

		pages_indexed, images_indexed, all_links, iterate_list_of_urls = url_handling.crawl_urls(final_urls, namespaces_to_ignore, cursor, pages_indexed, images_indexed, image_urls, links, external_links, discovered_urls, broken_urls, iterate_list_of_urls)

		log_contents(cursor, pages_indexed, images_indexed)

		with open(ROOT_DIRECTORY + "/data/all_links.csv","w") as f:
			wr = csv.writer(f)
			wr.writerow(["page_linking", "link_to", "datetime", "link_type", "anchor_text"])
			wr.writerows(all_links)

	#broken_links.check_for_invalid_links()

build_index()

test_queries.run_test_queries()

create_charts.plot_keyword_frequency()

create_charts.plot_linkrot_by_date()

create_charts.show_error_codes()

create_charts.calculate_index_size()
>>>>>>> c0e980441926b4504939b2fa460fb12f98d9e325
