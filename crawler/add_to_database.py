from bs4 import Comment
import requests
import datetime
import logging
import config
import mf2py
import json

def add_to_database(full_url, published_on, doc_title, meta_description, heading_info, page, pages_indexed, page_content, outgoing_links, crawl_budget, nofollow_all, main_page_content, h_card):
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

	h_card_to_index = None

	if len(h_card) == 0:
		mf2_parsed = mf2py.parse(url=full_url.split("/")[0] + "//" + full_url.split("/")[2])
		for item in mf2_parsed['items']:
			if item['type'] == 'h-card' or (type(item["type"]) == list and "h-card" in item['type']):
				if item.get("properties"):
					h_card_to_index = item["properties"]
					break
	else:
		h_card_to_index = h_card[0]

	if nofollow_all == True:
		nofollow_all = "true"
	else:
		nofollow_all = "false"

	if type(published_on) == dict and published_on.get("datetime") != None:
		date_to_record = published_on["datetime"].split("T")[0]
	else:
		date_to_record = ""

	# find out if page is home page
	if full_url.replace("https://", "").replace("http://", "").strip("/").count("/") == 0:
		is_homepage = True
	else:
		is_homepage = False

	record = {
		"title": doc_title,
		"meta_description": meta_description,
		"url": full_url,
		"published_on": date_to_record,
		"h1": ", ".join(heading_info["h1"]),
		"h2": ", ".join(heading_info["h2"]),
		"h3": ", ".join(heading_info["h3"]),
		"h4": ", ".join(heading_info["h4"]),
		"h5": ", ".join(heading_info["h5"]),
		"h6": ", ".join(heading_info["h6"]),
		"length": length,
		"page_content": str(page_content),
		"incoming_links": 0,
		"page_text": page_content.get_text(),
		"outgoing_links": outgoing_links,
		"domain": full_url.split("/")[2],
		"word_count": len(main_page_content.get_text().split(" ")),
		"last_crawled": datetime.datetime.today().strftime("%Y-%m-%d %H:%M:%S"),
		"favicon": favicon,
		"referring_domains_to_site": 0, # updated when index is rebuilt
		"internal_incoming_links": 0, # not actively used
		"http_headers": str(page.headers),
		"page_is_nofollow": nofollow_all,
		"h_card": json.dumps(h_card_to_index),
		"is_homepage": is_homepage,
	}

	# results currently being saved to a file, so no need to run this code

	# check_if_indexed = requests.post("https://es-indieweb-search.jamesg.blog/check?url={}".format(full_url), headers={"Authorization": "Bearer {}".format(config.ELASTICSEARCH_API_TOKEN)}).json()

	# if len(check_if_indexed) > 0:
	# 	record["incoming_links"] = check_if_indexed[0]["_source"]["incoming_links"]
	# else:
	# 	record["incoming_links"] = 0

	with open("results.json", "a+") as f:
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