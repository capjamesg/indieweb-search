from bs4 import Comment
import requests
import datetime
import logging
import config
import hashlib
import json

def add_to_database(full_url, published_on, doc_title, meta_description, category, heading_info, page, pages_indexed, page_content, outgoing_links, crawl_budget, reindex, nofollow_all):
	# get last modified date

	if page != "" and page.headers:
		length = page.headers.get("content-length")
	else:
		length = len(page_content)

	# remove script and style tags from page_content

	for script in page_content(["script", "style"]):
		script.decompose()

	# remove comments

	comments = page_content.findAll(text=lambda text:isinstance(text, Comment))
	[comment.extract() for comment in comments]

	# get site favicon
	favicon = page_content.find("link", rel="shortcut icon")

	if favicon:
		favicon = favicon.get("href")
	else:
		favicon = ""

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
		"favicon": favicon,
		"referring_domains_to_site": 0, # updated when index is rebuilt
		"internal_incoming_links": 0, # not actively used
		"http_headers": str(page.headers),
		"page_is_nofollow": nofollow_all,
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