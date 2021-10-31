from bs4 import Comment
import requests
import datetime
import logging
import config
import mf2py
import json

def add_to_database(full_url, published_on, doc_title, meta_description, heading_info, page, pages_indexed, page_content, outgoing_links, crawl_budget, nofollow_all, main_page_content, original_h_card, thin_content=False):
	# get last modified date

	if page != "" and page.headers:
		length = page.headers.get("content-length")
	else:
		length = len(page_content)

	# remove script and style tags from page_content

	for script in page_content(["script", "style"]):
		script.decompose()

	# remove HTML comments

	comments = page_content.findAll(text=lambda text:isinstance(text, Comment))
	[comment.extract() for comment in comments]

	# get site favicon
	favicon = page_content.find("link", rel="shortcut icon")

	if favicon:
		favicon = favicon.get("href")
	else:
		favicon = ""

	h_card = []
	h_card_url = None
	category = None

	h_entry = mf2py.parse(page_content)

	for i in h_entry["items"]:
		if i['type'] == ['h-entry']:
			if i['properties'].get('author'):
				# if author is h_card
				if type(i['properties']['author'][0]) == dict and i['properties']['author'][0].get('type') == ['h-card']:
					h_card = i['properties']['author'][0]
					break

				elif type(i['properties']['author']) == list:
					h_card = i['properties']['author'][0]
					break

			# category
			if i['properties'].get('category'):
				category = ", ".join(i['properties']['category'])
				
	# if rel=author, look for h-card on the rel=author link
	if h_card == []:
		if h_entry.get("rels") and h_entry["rels"].get("author"):
			rel_author = h_entry['rels']['author']

			if rel_author:
				h_card_url = rel_author[0]

	if h_card_url:
		new_h_card = mf2py.parse(url=h_card_url)

		if new_h_card.get("rels") and new_h_card.get("rels").get("me"):
			rel_mes = new_h_card['rels']['me']
		else:
			rel_mes = []

		for j in new_h_card["items"]:
			if j.get('type') and j.get('type') == ['h-card'] and j['properties']['url'] == rel_author and j['properties'].get('uid') == j['properties']['url']:
				h_card = j
				break
			elif j.get('type') and j.get('type') == ['h-card'] and j['properties'].get('url') in rel_mes:
				h_card = j
				break
			elif j.get('type') and j.get('type') == ['h-card'] and j['properties']['url'] == rel_author:
				h_card = j
				break

	if h_card == [] or h_card == None:
		h_card = original_h_card

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

	# get featured image if one is available
	# may be presented in featured snippets
	featured_image = None

	if page_content.find(".u-photo"):
		featured_image = page_content.find(".u-photo").get("src")

	if featured_image == None and page_content.find("meta", property="og:image"):
		featured_image = page_content.find("meta", property="og:image").get("src")

	if featured_image == None and page_content.find("meta", property="twitter:image"):
		featured_image = page_content.find("meta", property="twitter:image").get("src")

	if featured_image == None:
		featured_image = ""

	# use p-name in place of title tag if one is available
	if page_content.find(".p-name"):
		title = page_content.find(".p-name").text
		if len(title.split(" ")) > 10:
			title = title.split(" ", 10)[0] + "..."
	else:
		title = doc_title

	contains_javascript = False

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
		"contains_javascript": contains_javascript
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