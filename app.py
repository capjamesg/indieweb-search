from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify
from textblob import TextBlob, Word
from spellchecker import SpellChecker
import sqlite3
import datetime
import math
import json
import csv
import re

app = Flask(__name__, static_folder="static", static_url_path="")

spell = SpellChecker()

def initialize_spell_checker():
	connection = sqlite3.connect("search.db")
	cursor = connection.cursor()

	keywords = cursor.execute("SELECT keywords FROM posts;").fetchall()
	for k in keywords:
		words_to_add = []
		for l in k.split(", "):
			words_to_add.append(l)

		spell.word_frequency.load_words(words_to_add)

# This code shows the date a post was published on
# {% if r[3] != "Page" %} {{ r[4] | strftime }} - {% endif %}
# The code has been removed from the template, but it can be added back in if needed

# @app.template_filter('strftime')
# def jinja2_filter_datetime(value_to_parse):
#     value_to_parse = datetime.datetime.strptime(value_to_parse, "%Y-%m-%d")
#     return value_to_parse.strftime("%d %B, %Y")

def parse_advanced_search(advanced_filter_to_search, query_with_handled_spaces, query_params, query_values_in_list, operand):
	# Advanced search term to look for (i.e. before:")
	look_for = query_with_handled_spaces.find(advanced_filter_to_search)
	if look_for != -1:
		# Find value that I'm looking for (date, category, etc.)
		get_value = re.findall(r'{}([^"]*)"'.format(advanced_filter_to_search), query_with_handled_spaces)

		# Write query param that will be used in final query, add to list of query params

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

	query_params, query_values_in_list, query_with_handled_spaces = parse_advanced_search('category:"', query_with_handled_spaces, query_params, query_values_in_list, "category = ?")
	query_params, query_values_in_list, query_with_handled_spaces = parse_advanced_search('before:"', query_with_handled_spaces, query_params, query_values_in_list, "published <= date(?)")
	query_params, query_values_in_list, query_with_handled_spaces = parse_advanced_search('after:"', query_with_handled_spaces, query_params, query_values_in_list, "published >= date(?)")
	
	return query_params, query_values_in_list, query_with_handled_spaces

@app.route("/")
def home():
	return render_template("submit.html")

@app.route("/results", methods=["GET", "POST"])
def results_page():
	page = request.args.get("page")
	is_json = request.args.get("json")

	if request.form.get("type") == "image":
		return redirect("https://search.jamesg.blog/results?{}&type=image".format(request.args.get("query")))
	if request.args.get("query"):
		connection = sqlite3.connect("search.db")

		query_with_handled_spaces = request.args.get("query").replace("--", "")

		allowed_chars = [" ", '"', ":", "-", "/", "."]

		cleaned_value = ''.join(e for e in query_with_handled_spaces if e.isalnum() or e in allowed_chars)

		query_params, query_values_in_list, query_with_handled_spaces = handle_advanced_search(query_with_handled_spaces)

		# Added support for inurl: queries. Not being used.

		# if 'inurl:"' in query_with_handled_spaces:
		# 	query_params += "AND url LIKE ?"
		# 	# Replce percentage signs
		# 	value_to_add = "%" + re.findall(r'{}([^"]*)"'.format('inurl:"'), query_with_handled_spaces)[0] + "%"
		# 	query_values_in_list.append(value_to_add)
		# 	query_with_handled_spaces = query_with_handled_spaces.replace('{}{}"'.format('inurl:"', re.findall(r'{}([^"]*)"'.format('inurl:"'), query_with_handled_spaces)[0]), "")

		cleaned_value_for_query = ''.join(e for e in query_with_handled_spaces if e.isalnum() or e == " ")
		
		if len(cleaned_value_for_query) > 0:
			with connection:
				cursor = connection.cursor()

				pagination = "LIMIT 10"

				if page:
					# If page cannot be converted into an integer, redirect to homepage
					# Added for security

					try:
						if int(page) > 1:
							pagination = "LIMIT 10 OFFSET {}".format((int(page) - 1) * 10)
					except:
						return redirect("https://search.jamesg.blog")
				else:
					page = 1

				if request.args.get("order") == "date_asc":
					order = "published ASC"
				elif request.args.get("order") == "date_desc":
					order = "published DESC"
				else:
					order = "score, published DESC"
				
				if not request.args.get("type") and request.args.get("type") != "image":
					query = 'SELECT title, highlight(posts, 1, "<b>", "</b>") description, url, category, published, keywords, page_content, h1, h2, h3, h4, h5, h6, bm25(posts, 10.0, 5.0, 1.0, 0.0, 0.0, 7.5, 7.5, 4.0, 3.0, 2.0, 1.0, 0.5, 0.5) as score FROM posts WHERE posts MATCH ? {} ORDER BY {} {};'.format(query_params, order, pagination)
					result_num = "SELECT COUNT(url) FROM posts WHERE posts MATCH ? {};".format(query_params)
				else:
					if order != "score":
						order = "score"
					query = "SELECT Image.post_url, highlight(images, 1, '<b>', '</b>') alt_text, Image.image_src, Image.published, bm25(images, 2.5, 10.0, 5.0, 0.0) as score FROM posts as Post JOIN images as Image On Post.url = Image.post_url WHERE images MATCH ? {} ORDER BY {} {};".format(query_params, order, pagination)
					result_num = "SELECT COUNT(image_src) FROM posts as Post JOIN images as Image ON Post.url = Image.post_url WHERE images MATCH ? {};".format(query_params, order)

				query_values_in_list.insert(0, cleaned_value_for_query)

				rows = cursor.execute(query, query_values_in_list).fetchall()
				num_of_results = cursor.execute(result_num, query_values_in_list).fetchone()[0]

				if len(rows) == 0:
					out_of_bounds_page = True
				else:
					out_of_bounds_page = False

				if request.args.get("type") == "image":
					base_results_query="/results?query={}&type=image".format(cleaned_value)
				else:
					base_results_query="/results?query={}".format(cleaned_value)

				# Spelling suggestion for typos

				identify_mistakes = spell.unknown(cleaned_value_for_query.split(" "))

				final_query = ""

				suggestion = False

				for w in cleaned_value_for_query.split(" "):
					if w in identify_mistakes:
						final_query += spell.correction(w) + " "
						suggestion = True
					else:
						final_query += w + " "

				# Only for testing, should not be in prod
				if is_json:
					return jsonify(rows)

				return render_template("results.html",
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
					suggestion_made=suggestion)
		else:
			return redirect(url_for("home"))
	else:
		return redirect(url_for("home"))

@app.route("/robots.txt")
def robots():
	return send_from_directory(app.static_folder, "robots.txt")

@app.route("/stats")
def show_indexing_stats():
	return send_from_directory(app.static_folder, "index_stats.json")

@app.route("/log", methods=["GET", "POST"])
def show_indexing_log():
	k = request.args.get("k")
	issue_search = request.args.get("issue_search")

	if k == "r34sqCiKRR9zedhz":
		connection = sqlite3.connect("search.db")

		with connection:
			cursor = connection.cursor()
			if issue_search:
				index_status = cursor.execute("SELECT * FROM crawl_errors where message = ?;", (issue_search, )).fetchall()
			else:
				index_status = cursor.execute("SELECT * FROM crawl_errors;").fetchall()

			with open("static/index_stats.json", "r") as f:
				index_stats = json.load(f)

			unique_error_types = cursor.execute("SELECT DISTINCT message FROM crawl_errors;").fetchall()
		
			return render_template("index_log.html", results=index_status, index_stats=index_stats, unique_error_types=unique_error_types, page="log")
	else:
		return jsonify({"error": "You must be authenticated to view this resource."}), 403

@app.route("/log/test-queries")
def show_test_queries():
	k = request.args.get("k")

	if k == "r34sqCiKRR9zedhz":
		with open("data/test_queries.md", "r") as f:
			test_queries = f.readlines()

		with open("static/index_stats.json", "r") as f:
			index_stats = json.load(f)
		
		return render_template("test_queries.html", test_queries=test_queries, index_stats=index_stats, page="test-queries")
	else:
		return jsonify({"error": "You must be authenticated to view this resource."}), 403

@app.route("/log/past-crawls")
def show_past_crawls():
	k = request.args.get("k")

	if k == "r34sqCiKRR9zedhz":
		with open("data/index_stats.csv", "r") as f:
			data = csv.reader(f)

			past_indexes = [d for d in data]
		
		return render_template("past_indexes.html", past_indexes=past_indexes, page="past-crawls")
	else:
		return jsonify({"error": "You must be authenticated to view this resource."}), 403

@app.route('/images/<path:path>')
def send_static_images(path):
    return send_from_directory("static/images", path)

@app.route("/advanced")
def advanced_search():
    return render_template("advanced_search.html")

@app.errorhandler(404)
def page_not_found(e):
    return render_template("error.html"), 404

@app.errorhandler(500)
def server_error(e):
    return render_template("error.html", server_error=True), 500