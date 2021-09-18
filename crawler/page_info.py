from typing import final
from textblob import WordList
from nltk.corpus import stopwords
import crawler.url_handling
import datetime

# Get last index start time
# with open("static/index_stats.json") as file:
# 	index_stats = json.load(file)
# 	last_index_start = index_stats.get("last_index_start")

stopwords = set(stopwords.words('english'))

# Add the words below to the stopwords set
excluded_words = {"one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "James", "every", "people", "thing", "first"}

stopwords.update(excluded_words)

full_stopwords_list = {}

for word in stopwords:
	full_stopwords_list[word] = ""

# def check_url_for_errors(page_url, discovered_urls, broken_urls):
# 	"""
# 		Checks if a URL is malformed.
# 	"""

# 	if page_url.islower() == False:
# 		crawler.url_handling.log_error(page_url, 200, "URL contains an uppercase character.", discovered_urls, broken_urls)

# 	if "_" in page_url:
# 		crawler.url_handling.log_error(page_url, 200, "URL contains an underscore.", discovered_urls, broken_urls)

# 	if len(page_url) > 100:
# 		crawler.url_handling.log_error(page_url, 200, "URL is {} characters long (too long).".format(len(page_url)), discovered_urls, broken_urls)

def get_page_info(page_text, page_desc_soup, page_url):
	"""
		Scrapes page information for index and returns it to be added to the database later.
	"""
	
	# check_url_for_errors(page_url, discovered_urls, broken_urls)

	contains_hfeed = page_desc_soup.find(class_="h-feed")

	if contains_hfeed:
		# get all h-entry elements
		h_entries = contains_hfeed.find_all(class_="h-entry")

		if len(h_entries) > 5 and page_url.count("/") > 4:
			return page_text, page_desc_soup, [], [], [], [], [], [], True

		# get date of first hentry
		if len(h_entries) > 0:
			first_hentry_date = h_entries[0].find(class_="dt-published")

			if first_hentry_date and first_hentry_date.get("datetime"):
				# if published before 3 weeks ago
				if first_hentry_date.get("datetime") < (datetime.datetime.now() - datetime.timedelta(weeks=3)).isoformat() and page_url.count("/") > 3:
					print("{} marked as follow, noindex as it is a feed".format(page_url))
					return page_text, page_desc_soup, first_hentry_date.get("datetime"), [], [], [], [], [], True

	published_on = page_desc_soup.find("time", attrs={"class":"dt-published"})

	meta_description = ""

	if page_desc_soup.find("meta", {"name":"description"}) != None and page_desc_soup.find("meta", {"name":"description"}).get("content") and page_desc_soup.find("meta", {"name":"description"})["content"] != "":
		meta_description = page_desc_soup.find("meta", {"name":"description"})["content"]

	elif page_desc_soup.find("meta", {"name":"og:description"}) != None and page_desc_soup.find("meta", {"name":"og:description"}).get("content") and page_desc_soup.find("meta", {"name":"og:description"})["content"] != "":
		meta_description = page_desc_soup.find("meta", {"name":"og:description"})["content"]

	elif page_desc_soup.find("meta", {"property":"og:description"}) != None and page_desc_soup.find("meta", {"property":"og:description"}).get("content") and page_desc_soup.find("meta", {"property":"og:description"})["content"] != "":
		meta_description = page_desc_soup.find("meta", {"property":"og:description"})["content"]

	if meta_description == "":
		summary = page_desc_soup.select("p-summary")

		if summary:
			meta_description = summary[0].text

	if meta_description == "":
		# Use first paragraph as meta description if one can be found
		# get paragraph after h1

		e_content = page_desc_soup.find(class_="e-content")

		if e_content and len(e_content) > 0:
			potential_meta_description = e_content.find_all("p")
			if potential_meta_description and len(potential_meta_description) > 0:
				meta_description = potential_meta_description[0].text
				if len(meta_description) < 50:
					meta_description = ""

	if meta_description == "" or meta_description == None:
		h1 = page_desc_soup.find("h1")
		
		if h1:
			paragraph_to_use_for_meta_desc = h1.find_next("p")

			if paragraph_to_use_for_meta_desc and len(paragraph_to_use_for_meta_desc.text) < 50:
				paragraph_to_use_for_meta_desc = h1.find_next("p").find_next("p")
				if paragraph_to_use_for_meta_desc:
					meta_description = paragraph_to_use_for_meta_desc.text
			elif paragraph_to_use_for_meta_desc:
				meta_description = paragraph_to_use_for_meta_desc.text

	if meta_description == "" or meta_description == None:
		h2 = page_desc_soup.find_all("h2")

		if h2 and len(h2) > 0:
			paragraph_to_use_for_meta_desc = h2[0].find_next("p")
			if paragraph_to_use_for_meta_desc != None:
				meta_description = paragraph_to_use_for_meta_desc.text

	if meta_description == None:
		meta_description = ""
	
	# Only get first 180 characters of meta description (and don't chop a word)

	final_meta_description = ""
	char_count = 0

	for w in meta_description.split(" "):
		char_count += len(w)
		final_meta_description += w + " "

		if char_count > 180:
			final_meta_description += "..."
			break

	remove_doc_title_from_h1_list = False

	if page_desc_soup.find("title") != None:
		doc_title = page_desc_soup.find("title").text
	elif page_desc_soup.find("h1") != None:
		doc_title = page_desc_soup.find("h1").text
		remove_doc_title_from_h1_list = True
	else:
		doc_title = page_url

	if doc_title == "":
		doc_title = page_url
	
	if page_desc_soup.find("a", attrs={"class":"p-category"}) != None:
		category = page_desc_soup.find("a", attrs={"class":"p-category"}).text
	else:
		category = "Page"

	return page_text, page_desc_soup, published_on, final_meta_description, doc_title, category, remove_doc_title_from_h1_list, False