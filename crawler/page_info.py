from textblob import WordList
from nltk.corpus import stopwords
import crawler.url_handling
import logging
import spacy
import pytextrank
from spellchecker import SpellChecker

spell = SpellChecker()

# Load data analysis textrank model

nlp = spacy.load("en_core_web_md")

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

nlp.add_pipe("textrank")

def check_url_for_errors(page_url, discovered_urls, broken_urls):
	"""
		Checks if a URL is malformed.
	"""

	if page_url.islower() == False:
		crawler.url_handling.log_error(page_url, 200, "URL contains an uppercase character.", discovered_urls, broken_urls)

	if "_" in page_url:
		crawler.url_handling.log_error(page_url, 200, "URL contains an underscore.", discovered_urls, broken_urls)

	if len(page_url) > 100:
		crawler.url_handling.log_error(page_url, 200, "URL is {} characters long (too long).".format(len(page_url)), discovered_urls, broken_urls)

def get_page_info(page_text, page_desc_soup, page_url, discovered_urls, broken_urls, cursor):
	"""
		Scrapes page information for index and returns it to be added to the database later.
	"""
	
	check_url_for_errors(page_url, discovered_urls, broken_urls)

	# if page_text:
	# 	doc = nlp(page_text.text)

	# 	# mistakes = spell.unknown(page_text.text)

	# 	# mistakes = [w for w in mistakes]

	# 	# if len(mistakes) > 0:
	# 	# 	crawler.url_handling.log_error(page_url, 200, "Page contains spelling mistakes: {}".format(mistakes), discovered_urls, broken_urls)

	# 	# Exclude my name from keywords

	# 	important_phrases = [p.text.replace("\n", "").lower() for p in doc._.phrases if float(p.count) > 2 and p.rank > 0.03 and full_stopwords_list.get(p.text.split(" ")[0].lower()) == None and not any(map(str.isdigit, p.text))][:7]
	# else:
	# 	important_phrases = []

	# important_phrases = WordList(important_phrases).lemmatize()

	# # Exclude stopwords from keywords
	# final_phrases = [p.replace("\t", "").replace("\n", "") for p in important_phrases if p not in stopwords and p.replace("\t", "").replace("\n", "").isalnum()]

	# # if TextBlob(i).tags != []:
	# # 	if TextBlob(i).tags[0][1] == "NNP":
	# # 		final_phrases.append("what is {}".format(i))
	# # elif "recipe" in i:
	# # 	final_phrases.append("how to {}", "make")

	# # Remove duplicates from important phrases
	# important_phrases = list(set(final_phrases))

	# if "javascript" in important_phrases:
	# 	important_phrases.remove("javascript")

	# print(important_phrases)

	# logging.debug("Important phrases: " + ", ".join(important_phrases))

	important_phrases = ""

	# check_if_support_mf2_as_hentry = page_desc_soup.find(class_="h-entry")

	# if check_if_support_mf2_as_hentry:
	# 	check_p_name = page_desc_soup.find(class_="p-name")
	# 	check_e_content = page_desc_soup.find(class_="e-content")

	# 	if check_p_name and len(check_p_name) == 0:
	# 		crawler.url_handling.log_error(page_url, 200, "Page marked up as h-entry but is missing p-name.", discovered_urls, broken_urls)

	# 	if check_e_content and len(check_e_content) == 0:
	# 		crawler.url_handling.log_error(page_url, 200, "Page marked up as h-entry but is missing e-content.", discovered_urls, broken_urls)

	published_on = page_desc_soup.find("time", attrs={"class":"dt-published"})

	meta_description = ""

	if page_desc_soup.find("meta", {"name":"description"}) != None and page_desc_soup.find("meta", {"name":"description"})["content"] != "":
		meta_description = page_desc_soup.find("meta", {"name":"description"})["content"]
	elif page_desc_soup.find("meta", {"name":"og:description"}) != None and page_desc_soup.find("meta", {"name":"description"})["content"] != "":
		meta_description = page_desc_soup.find("meta", {"name":"og:description"})["content"]

	if meta_description == "":
		summary = page_desc_soup.select("p-summary")

		if summary:
			meta_description = summary[0].text

	if meta_description == "":
		crawler.url_handling.log_error(page_url, 200, "Page is missing a meta description.", discovered_urls, broken_urls)
		# Use first paragraph as meta description if one can be found
		paragraphs = page_text.find_all("p")
		for para in paragraphs:
			# Find first paragraph with 50 or more words
			if len(para.text) > 50:
				meta_description = para.text
				break
			else:
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

	meta_description = final_meta_description

	remove_doc_title_from_h1_list = False

	if page_desc_soup.find("title") != None:
		doc_title = page_desc_soup.find("title").text
	elif page_desc_soup.find("h1") != None:
		crawler.url_handling.log_error(page_url, 200, "Page is missing a title tag.", discovered_urls, broken_urls)
		doc_title = page_desc_soup.find("h1").text
		remove_doc_title_from_h1_list = True
	else:
		crawler.url_handling.log_error(page_url, 200, "Page is missing a title tag.", discovered_urls, broken_urls)
		crawler.url_handling.log_error(page_url, 200, "Page is missing a <h1> tag.", discovered_urls, broken_urls)
		doc_title = page_url

	if doc_title == "":
		crawler.url_handling.log_error(page_url, 200, "Page is missing a title tag.", discovered_urls, broken_urls)
		doc_title = page_url

	if page_desc_soup.find("title") == None:
		# Error code is 200 because page has already been validated as 200 by this point
		crawler.url_handling.log_error(page_url, 200, "Page has no title.", discovered_urls, broken_urls)
	elif page_desc_soup.find("title").text == "":
		crawler.url_handling.log_error(page_url, 200, "Page has no title.", discovered_urls, broken_urls)
	
	if page_desc_soup.find("a", attrs={"class":"p-category"}) != None:
		category = page_desc_soup.find("a", attrs={"class":"p-category"}).text
	else:
		category = "Page"

	if page_desc_soup.find("title") and page_desc_soup.find("h1") and page_desc_soup.find("title").text == page_desc_soup.find("h1").text:
		crawler.url_handling.log_error(page_url, 200, "Page title is same as h1.", discovered_urls, broken_urls)

	if page_desc_soup.find("title"):
		if len(page_desc_soup.find("title").text) > 75:
			crawler.url_handling.log_error(page_url, 200, "Page title is too long ({} characters).".format(len(page_desc_soup.find("title").text)), discovered_urls, broken_urls)

		# check if title in db
		title_in_db = cursor.execute("SELECT * FROM posts WHERE title = ? AND NOT url = ? LIMIT 1;", (page_desc_soup.find("title").text, page_url, )).fetchall()
		if len(title_in_db) > 0 and page_desc_soup.find("title") != "":
			crawler.url_handling.log_error(page_url, 200, 'Page title ("{}") is already used on another page.'.format(page_desc_soup.find("title").text), discovered_urls, broken_urls)

	if len(meta_description) > 0:
		# check if meta description in db
		meta_description_in_db = cursor.execute("SELECT * FROM posts WHERE title = ? AND NOT url = ? LIMIT 1;", (meta_description, page_url,)).fetchall()
		if len(meta_description_in_db) > 0 and meta_description != "":
			crawler.url_handling.log_error(page_url, 200, 'Meta description ("{}") is already used on another page.'.format(meta_description), discovered_urls, broken_urls)

	# Remove links from page text because they might cause searches to be less accurate
	# for a in page_text.find_all("a"):
	# 	a.replaceWith("")

	return page_text, page_desc_soup, published_on, meta_description, doc_title, category, important_phrases, remove_doc_title_from_h1_list