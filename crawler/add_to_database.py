import crawler.identify_special_snippet as identify_special_snippet
import crawler.authorship_discovery as authorship_discovery
import crawler.post_type_discovery as post_type_discovery	
from bs4 import Comment
import datetime
import logging
import mf2py
import json

def add_to_database(full_url, published_on, doc_title, meta_description, heading_info, page, 
	pages_indexed, page_content, outgoing_links, crawl_budget, nofollow_all, main_page_content, 
	original_h_card, hash, thin_content=False):

	# the program will try to populate all of these values before indexing a document
	category = None
	special_snippet = {}
	h_card = None
	favicon = ""
	length = len(page_content)
	is_homepage = False
	nofollow_all = "false"
	date_to_record = ""
	contains_javascript = False

	# get last modified date

	if page != "" and page.headers:
		length = page.headers.get("content-length")

	# remove script and style tags from page_content

	for script in page_content(["script", "style"]):
		script.decompose()

	# remove HTML comments
	# we don't want to include these in rankings

	comments = page_content.findAll(text=lambda text:isinstance(text, Comment))
	[comment.extract() for comment in comments]

	# get site favicon
	favicon = page_content.find("link", rel="shortcut icon")

	if favicon:
		favicon = favicon.get("href")

	h_entry_object = mf2py.parse(page_content)

	special_snippet, h_card = identify_special_snippet.find_snippet(page_content, h_card)

	if h_card == []:
		h_card = authorship_discovery.discover_author(h_card, h_entry_object, full_url, original_h_card)

	page_as_h_entry = None

	for item in h_entry_object:
		if item["type"] and item["type"] == ["h-entry"]:
			page_as_h_entry = item

	if nofollow_all == True:
		nofollow_all = "true"

	if type(published_on) == dict and published_on.get("datetime") != None:
		date_to_record = published_on["datetime"].split("T")[0]

	# find out if page is home page
	if full_url.replace("https://", "").replace("http://", "").strip("/").count("/") == 0:
		is_homepage = True

	# get featured image if one is available
	# may be presented in featured snippets
	featured_image = None

	if page_content.find(".u-featured"):
		featured_image = page_content.find(".u-featured").get("src")

	elif page_content.find(".u-photo"):
		featured_image = page_content.find(".u-photo").get("src")

	elif page_content.find("meta", property="og:image"):
		featured_image = page_content.find("meta", property="og:image").get("src")

	elif page_content.find("meta", property="twitter:image"):
		featured_image = page_content.find("meta", property="twitter:image").get("src")

	else:
		featured_image = ""

	# use p-name in place of title tag if one is available
	if page_content.select(".p-name"):
		title = page_content.select(".p-name")[0].text
		if title.strip(" ") != "" and len(title) > 5:
			if len(title.split(" ")) > 10:
				title = title.split(" ", 10)[0] + "..."
	else:
		title = doc_title

	# page contains javascript
	if page_content.find("script"):
		contains_javascript = True
		
	record = {
		"title": title,
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
		"h_card": json.dumps(h_card),
		"is_homepage": is_homepage,
		"category": category,
		"featured_image": featured_image,
		"thin_content": thin_content,
		"contains_javascript": contains_javascript,
		"page_hash": hash,
		"special_snippet": special_snippet
	}

	if page_as_h_entry != None:
		post_type = post_type_discovery.get_post_type(page_as_h_entry)
		record["post_type"] = post_type

	with open("results.json", "a+") as f:
		f.write(json.dumps(record))
		f.write("\n")

	logging.info("indexed new page {} ({}/{})".format(full_url, pages_indexed, crawl_budget))

	pages_indexed += 1

	return pages_indexed