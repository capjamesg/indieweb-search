import sqlite3
import datetime
import math
import re
import spacy
from flask import render_template, request, redirect, send_from_directory, jsonify, Blueprint
from spellchecker import SpellChecker
from . import search_result_features
from .config import ROOT_DIRECTORY

main = Blueprint("main", __name__, static_folder="static", static_url_path="")

spell = SpellChecker()

nlp = spacy.load('en_core_web_sm')

# def initialize_spell_checker():
# 	connection = sqlite3.connect(ROOT_DIRECTORY + "/search.db")

# 	cursor = connection.cursor()

# 	keywords = cursor.execute("SELECT keywords FROM posts;").fetchall()
# 	for k in keywords:
# 		words_to_add = []
# 		for l in k[0].split(", "):
# 			words_to_add.append(l)

# 		spell.word_frequency.load_words(words_to_add)

# initialize_spell_checker()

# This code shows the date a post was published on
# {% if r[3] != "Page" %} {{ r[4] | strftime }} - {% endif %}
# The code has been removed from the template, but it can be added back in if needed

# @app.template_filter('strftime')
# def jinja2_filter_datetime(value_to_parse):
# 	value_to_parse = datetime.datetime.strptime(value_to_parse, "%Y-%m-%d")
# 	return value_to_parse.strftime("%d %B, %Y")

def parse_advanced_search(advanced_filter_to_search, query_with_handled_spaces, query_params, query_values_in_list, operand, inverted=False):
	# Advanced search term to look for (i.e. before:")
	look_for = query_with_handled_spaces.find(advanced_filter_to_search)
	if look_for != -1:
		# Find value that I'm looking for (date, category, etc.)
		get_value = re.findall(r'{}([^"]*)"'.format(advanced_filter_to_search), query_with_handled_spaces)

		if advanced_filter_to_search == "site:":
			get_value[0] = get_value[0].replace("https://", "").replace("http://", "").split("/")[0]

		# Write query param that will be used in final query, add to list of query params

		if inverted == True:
			query_params += "AND NOT {}".format(operand)
		else:
			query_params += "AND {}".format(operand)
			
		query_with_handled_spaces = query_with_handled_spaces.replace('{}{}"'.format(advanced_filter_to_search, get_value[0]), "")

		# Format date as string if user provides before: or after: value then append date to list of query values
		# Otherwise append value to list of query values

		if "before" in advanced_filter_to_search or "after" in advanced_filter_to_search:
			query_values_in_list.append(datetime.datetime.strptime(get_value[0], "%Y-%d-%m"))
		else:
			query_values_in_list.append(get_value[0].replace('"', ""))

	return query_params, query_values_in_list, query_with_handled_spaces

# Process category search and defer dates to parse_advanced_search function
def handle_advanced_search(query_with_handled_spaces):
	query_params = ""

	query_values_in_list = []

	if 'not category:"' in query_with_handled_spaces or 'not inurl:' in query_with_handled_spaces:
		operand = "NOT"
	else:
		operand = ""

	query_params, query_values_in_list, query_with_handled_spaces = parse_advanced_search('category:"', query_with_handled_spaces, query_params, query_values_in_list, "category = ?", True)
	query_params, query_values_in_list, query_with_handled_spaces = parse_advanced_search('before:"', query_with_handled_spaces, query_params, query_values_in_list, "published <= date(?)")
	query_params, query_values_in_list, query_with_handled_spaces = parse_advanced_search('after:"', query_with_handled_spaces, query_params, query_values_in_list, "published >= date(?)")

	if 'inurl:"' in query_with_handled_spaces or 'site:"' in query_with_handled_spaces:
		if request.args.get("type") == "image":
			query_params += "AND Image.image_src {} LIKE ?".format(operand)
		else:
			query_params += "AND url {} LIKE ?".format(operand)

		value_to_add = "%" + re.findall(r'{}([^"]*)"'.format('inurl:"'), query_with_handled_spaces)[0] + "%"
		query_values_in_list.append(value_to_add)
		query_with_handled_spaces = query_with_handled_spaces.replace('{}{}"'.format('inurl:"', re.findall(r'{}([^"]*)"'.format('inurl:"'), query_with_handled_spaces)[0]), "")
	
	return query_params, query_values_in_list, query_with_handled_spaces

@main.route("/")
def home():
	return render_template("search/submit.html", title="IndieWeb Search")

@main.route("/results", methods=["GET", "POST"])
def results_page():
	page = request.args.get("page")
	is_json = request.args.get("json")

	special_result = False

	query_with_handled_spaces = request.args.get("query").replace("--", "")

	allowed_chars = [" ", '"', ":", "-", "/", "."]

	cleaned_value = ''.join(e for e in query_with_handled_spaces if e.isalnum() or e in allowed_chars)

	query_params, query_values_in_list, query_with_handled_spaces = handle_advanced_search(query_with_handled_spaces)

	cleaned_value_for_query = ''.join(e for e in query_with_handled_spaces if e.isalnum() or e == " " or e == ".").replace(".", " ")

	if request.form.get("type") == "image":
		return redirect("/results?{}&type=image".format(cleaned_value_for_query))

	if request.args.get("query"):
		connection = sqlite3.connect(ROOT_DIRECTORY + "/search.db")
		full_query_with_full_stops = ''.join(e for e in query_with_handled_spaces if e.isalnum() or e == " " or e == ".")
		
		if len(cleaned_value_for_query) > 0 or len(query_params) > 0:
			with connection:
				do_i_use = ""

				cursor = connection.cursor()

				pagination = "LIMIT 10"

				if page:
					# If page cannot be converted into an integer, redirect to homepage
					# Added for security

					try:
						if int(page) > 1:
							pagination = "LIMIT 10 OFFSET {}".format((int(page) - 1) * 10)
					except:
						return redirect("/")
				else:
					page = 1

				if request.args.get("order") == "date_asc":
					order = "published ASC"
				elif request.args.get("order") == "date_desc":
					order = "published DESC"
				else:
					order = "score, published DESC"

				preserved_value = cleaned_value_for_query
				cleaned_value_for_query = cleaned_value_for_query.replace("what is", "")

				if len(cleaned_value_for_query) > 0 and request.args.get("type") != "image":
					query_params = "posts MATCH ? " + query_params
				
					query_values_in_list.insert(0, cleaned_value_for_query)
				elif len(cleaned_value_for_query) > 0 and request.args.get("type") == "image":
					query_params = "images MATCH ? " + query_params
				
					query_values_in_list.insert(0, cleaned_value_for_query)
				else:
					# Get all text after the first AND
					query_params = "".join(query_params.split("AND")[1:])

				if "on this day" in cleaned_value_for_query:
					get_today_day_as_number = str(datetime.datetime.now().day).zfill(2)
					get_today_month_as_number = str(datetime.datetime.now().month).zfill(2)

					query = "SELECT * FROM posts WHERE published LIKE '202_-{}-{}';".format(get_today_month_as_number, get_today_day_as_number)
					result_num = "SELECT COUNT(url) FROM posts WHERE published LIKE '202_-{}-{}';".format(get_today_month_as_number, get_today_day_as_number)
				elif not request.args.get("type") and request.args.get("type") != "image":
					query = 'SELECT title, highlight(posts, 1, "<b>", "</b>") description, url, category, published, keywords, page_content, h1, h2, h3, h4, h5, h6, (bm25(posts, 10.0, 5.0, 1.0, 0.0, 0.0, 7.5, 7.5, 4.0, 3.0, 2.0, 1.0, 0.5, 0.5) + abs(pagerank)) as score, pagerank FROM posts WHERE {} ORDER BY {} {};'.format(query_params, order, pagination)
					result_num = "SELECT COUNT(url) FROM posts WHERE {};".format(query_params)
				else:
					if order != "score":
						order = "score"

					query = "SELECT Image.post_url, highlight(images, 1, '<b>', '</b>') alt_text, Image.image_src, Image.published, Post.title, caption, bm25(images, 2.5, 10.0, 5.0, 0.0, 2.5, 10.0) as score FROM posts as Post JOIN images as Image On Post.url = Image.post_url WHERE {} ORDER BY {} {};".format(query_params, order, pagination)
					result_num = "SELECT COUNT(image_src) FROM posts as Post JOIN images as Image ON Post.url = Image.post_url WHERE {};".format(query_params)

				doc = nlp(preserved_value)

				without_stopwords = [token for token in doc if not token.is_stop and token.text != "who" and token.text != "is"]
				wiki_direct_result = cursor.execute("SELECT title, description, url, page_content from posts WHERE title LIKE ? AND url LIKE ? LIMIT 1", ("%" + cleaned_value_for_query.lower().strip() + "%", "%indieweb.org%", )).fetchall()
				# remove_punctuation = [token.text for token in without_stopwords if not token.is_punct]

				if "on this day" in cleaned_value_for_query:
					rows = cursor.execute(query).fetchall()
					num_of_results = cursor.execute(result_num).fetchone()[0]
				else:
					rows = cursor.execute(query, query_values_in_list).fetchall()
					num_of_results = cursor.execute(result_num, query_values_in_list).fetchone()[0]

					if request.args.get("type") != "image" and len(rows) > 0 and "random aeropress" not in cleaned_value and "generate aeropress" not in cleaned_value:
						if "what is" in preserved_value and wiki_direct_result:
							url = [row[2] for row in wiki_direct_result if cleaned_value_for_query.lower().strip() in row[0].lower() and row[2].startswith("https://indieweb.org")][0]
						elif len(rows) > 0:
							url = rows[0][2]
						else:
							url = None
							
						do_i_use, special_result = search_result_features.generate_featured_snippet(full_query_with_full_stops, cursor, special_result, nlp, url)

				# cleaned_value_for_query = " ".join(remove_punctuation)

				if len(rows) == 0:
					out_of_bounds_page = True

					identify_mistakes = spell.unknown(cleaned_value_for_query.split(" "))

					final_query = ""

					suggestion = False

					for w in cleaned_value_for_query.split(" "):
						if w in identify_mistakes:
							final_query += spell.correction(w) + " "
							suggestion = True
						else:
							final_query += w + " "
				else:
					out_of_bounds_page = False
					suggestion = False
					final_query = ""

				if request.args.get("type") == "image":
					base_results_query="/results?query={}&type=image".format(cleaned_value)
				else:
					base_results_query="/results?query={}".format(cleaned_value)

				# Spelling suggestion for typos

				if is_json:
					# check_if_api_key_valid = cursor.execute("SELECT * FROM user WHERE api_key = ?;", (request.args.get("api_key"),)).fetchone()
					# if check_if_api_key_valid and len(check_if_api_key_valid) > 0:
					return jsonify(rows)

				return render_template("search/results.html",
					results=rows,
					number_of_results=int(num_of_results),
					page=int(page),
					page_count=int(math.ceil(num_of_results / 10)),
					query=cleaned_value,
					results_type=request.args.get("type"),
					out_of_bounds_page=out_of_bounds_page,
					ordered_by=request.args.get("order"),
					base_results_query=base_results_query,
					corrected_text=final_query,
					suggestion_made=suggestion,
					special_result=special_result,
					do_i_use=do_i_use,
					title="Search results for '{}' query".format(cleaned_value))
		else:
			return redirect("/")
	else:
		return redirect("/")

@main.route("/robots.txt")
def robots():
	return send_from_directory(main.static_folder, "robots.txt")

@main.route('/images/<path:path>')
def send_static_images(path):
	return send_from_directory("static/images", path)

@main.route("/advanced")
def advanced_search():
	connection = sqlite3.connect("search.db")

	with connection:
		cursor = connection.cursor()

		count = cursor.execute("SELECT COUNT(*) FROM posts;").fetchone()[0]

	return render_template("search/advanced_search.html", count=count)

@main.route("/about")
def about():
	return render_template("search/about.html")