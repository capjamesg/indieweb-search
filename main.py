from flask import render_template, request, redirect, send_from_directory, jsonify, Blueprint
from .direct_answers import search_result_features
from spellchecker import SpellChecker
from . import config
import requests
import datetime
import json
import math
import re
import spacy

main = Blueprint("main", __name__, static_folder="static", static_url_path="")

spell = SpellChecker()

nlp = spacy.load('en_core_web_sm')

def parse_advanced_search(advanced_filter_to_search, query_with_handled_spaces, query_values_in_list):
	# Advanced search term to look for (i.e. before:")
	look_for = query_with_handled_spaces.find(advanced_filter_to_search)
	if look_for != -1:
		# Find value that I'm looking for (date, category, etc.)
		get_value = re.findall(r'{}([^"]*)"'.format(advanced_filter_to_search), query_with_handled_spaces)

		if advanced_filter_to_search == "site:":
			get_value[0] = get_value[0].replace("https://", "").replace("http://", "").split("/")[0]
			
		query_with_handled_spaces = query_with_handled_spaces.replace('{}{}"'.format(advanced_filter_to_search, get_value[0]), "")

		# Format date as string if user provides before: or after: value then append date to list of query values
		# Otherwise append value to list of query values

		if "before" in advanced_filter_to_search or "after" in advanced_filter_to_search:
			query_values_in_list.append(datetime.datetime.strptime(get_value[0], "%Y-%d-%m"))
		else:
			query_values_in_list.append(get_value[0].replace('"', ""))

	return query_values_in_list, query_with_handled_spaces

# Process category search and defer dates to parse_advanced_search function
def handle_advanced_search(query_with_handled_spaces):
	query_values_in_list = []

	if 'not category:"' in query_with_handled_spaces or 'not inurl:' in query_with_handled_spaces:
		operand = "NOT"
	else:
		operand = ""

	query_values_in_list, query_with_handled_spaces = parse_advanced_search('before:"', query_with_handled_spaces, query_values_in_list)
	query_values_in_list, query_with_handled_spaces = parse_advanced_search('after:"', query_with_handled_spaces, query_values_in_list)
	query_values_in_list, query_with_handled_spaces = parse_advanced_search('js:"', query_with_handled_spaces, query_values_in_list)

	if 'inurl:"' in query_with_handled_spaces:
		value_to_add = "%" + re.findall(r'{}([^"]*)"'.format('inurl:"'), query_with_handled_spaces)[0] + "%"
		query_values_in_list.append(value_to_add)
		query_with_handled_spaces = query_with_handled_spaces.replace('{}{}"'.format('inurl:"', re.findall(r'{}([^"]*)"'.format('inurl:"'), query_with_handled_spaces)[0]), "")

	if "site:" in query_with_handled_spaces:
		value_to_add = "%" + re.findall(r'{}([^"]*)"'.format('site:"'), query_with_handled_spaces)[0] + "%"
		query_values_in_list.append(value_to_add)
		query_with_handled_spaces = query_with_handled_spaces.replace('{}{}"'.format('site:"', re.findall(r'{}([^"]*)"'.format('site:"'), query_with_handled_spaces)[0]), "")
	
	return query_values_in_list, query_with_handled_spaces

@main.route("/")
def home():
	q = request.args.get("q")
	return render_template("search/submit.html", title="IndieWeb Search", query=q)

@main.route("/autocomplete")
def search_autocomplete():
	query = request.args.get("q")
	suggest = requests.get("https://es-indieweb-search.jamesg.blog/suggest?q={}&pw={}".format(query, config.ELASTICSEARCH_PASSWORD))

	return jsonify(suggest.json()), 200

@main.route("/results", methods=["GET", "POST"])
def results_page():
	page = request.args.get("page")
	is_json = request.args.get("json")
	site = request.args.get("site")

	if site and site == "jamesg.blog":
		# used for special jamesg.blog search redirect, not for open use
		site = "".join([x for x in site if x.isalpha() or x == "."])

		return redirect('/results?query=site:"{}"%20{}'.format(site, request.args.get("query")))

	special_result = False

	if not request.args.get("query"):
		return redirect("/")

	query_with_handled_spaces = request.args.get("query").replace("--", "").replace("  ", " ")

	allowed_chars = [" ", '"', ":", "-", "/", ".", "="]

	cleaned_value = ''.join(e for e in query_with_handled_spaces if e.isalnum() or e in allowed_chars)

	query_values_in_list, query_with_handled_spaces = handle_advanced_search(query_with_handled_spaces)

	cleaned_value_for_query = ''.join(e for e in query_with_handled_spaces if e.isalnum() or e == " " or e == ".")

	session = requests.Session()

	if cleaned_value.startswith("xray https://") or cleaned_value.startswith("xray http://"):
		return redirect("https://xray.p3k.io/parse?url={}".format(cleaned_value.replace("xray ", "")))

	if cleaned_value == "random":
		random_site = session.get("https://es-indieweb-search.jamesg.blog/random?pw={}".format(config.ELASTICSEARCH_PASSWORD)).json()["domain"]

		return redirect("https://{}/".format(random_site))

	if request.args.get("query"):
		full_query_with_full_stops = ''.join(e for e in query_with_handled_spaces if e.isalnum() or e == " " or e == ".")

		if len(cleaned_value_for_query) > 0:
			do_i_use = ""

			pagination = "0"

			if page:
				# If page cannot be converted into an integer, redirect to homepage

				try:
					if int(page) > 1:
						pagination = (int(page) - 1) * 10
				except:
					return redirect("/")
			else:
				page = 1

			if request.args.get("order") == "date_asc":
				order = "date_asc"
			elif request.args.get("order") == "date_desc":
				order = "date_desc"
			else:
				order = "score"

			cleaned_value_for_query = cleaned_value_for_query.replace("what is", "")

			if request.args.get("serp_as_json") and (request.args.get("serp_as_json") == "direct" or request.args.get("serp_as_json") == "results_page"):
				minimal = "true"
			else:
				minimal = "false"

			query_params = ""
			
			if "site:" in request.args.get("query"):
				query_params += "&site={}".format(query_values_in_list[-1].replace("%", ""))

			if request.args.get("query").startswith("discover"):
				query_params += "&discover=true"

			if "js:none" in request.args.get("query"):
				query_params += "&js=false"
			
			rows = session.get("https://es-indieweb-search.jamesg.blog/?pw={}&q={}&sort={}&from={}&to={}&minimal={}{}".format(config.ELASTICSEARCH_PASSWORD, cleaned_value_for_query.replace("review", "").replace("who is", "").replace("code", "").strip(), order, str(pagination), str(int(pagination)+10), minimal, query_params)).json()

			num_of_results = rows["hits"]["total"]["value"]
			rows = rows["hits"]["hits"]

			for r in rows:
				if r["_source"].get("h_card"):
					r["_source"]["h_card"] = json.loads(r["_source"]["h_card"])
				else:
					r["_source"]["h_card"] = None
			
			if page == 1:
				cleaned_value = cleaned_value.lower()
				if ("what is" in cleaned_value or "code" in cleaned_value or "markup" in cleaned_value or "meetup" in cleaned_value or "event" in cleaned_value or "review" in cleaned_value or "recipe" in cleaned_value or "what are" in cleaned_value  or "what were" in cleaned_value or "why" in cleaned_value or "how" in cleaned_value or "microformats" in cleaned_value) and "who is" not in cleaned_value:
					# remove stopwords from query
					original = cleaned_value_for_query
					cleaned_value_for_query = cleaned_value.replace("what is", "").replace("code", "").replace("markup", "").replace("what are", "").replace("why", "").replace("how", "").replace("what were", "").replace("to use", "").strip()

					wiki_direct_result = [item for item in rows if item["_source"]["url"].startswith("https://indieweb.org") \
						and "/" not in item["_source"]["title"] and cleaned_value_for_query.lower().strip() in item["_source"]["title"].lower()]
						
					microformats_wiki_direct_result = [item for item in rows if item["_source"]["url"].startswith("https://microformats.org/wiki/") \
						and "/" not in item["_source"]["title"] and cleaned_value_for_query.lower() in item["_source"]["title"].lower()]

					if wiki_direct_result:
						url = wiki_direct_result[0]["_source"]["url"]
						source = wiki_direct_result[0]["_source"]
					elif microformats_wiki_direct_result:
						url = microformats_wiki_direct_result[0]["_source"]["url"]
						source = microformats_wiki_direct_result[0]["_source"]
					elif len(rows) > 0:
						url = rows[0]["_source"]["url"]
						source = rows[0]["_source"]
					else:
						url = None
						source = None

					do_i_use, special_result = search_result_features.generate_featured_snippet(original, special_result, nlp, url, source)

					if do_i_use == "" and len(rows) > 1:
						do_i_use, special_result = search_result_features.generate_featured_snippet(original, special_result, nlp, rows[1]["_source"]["url"], rows[1]["_source"])
				elif len(rows) > 0 and rows[0]["_source"]["url"].startswith("https://jamesg.blog"):
					url = rows[0]["_source"]["url"]
					source = rows[0]["_source"]

					do_i_use, special_result = search_result_features.generate_featured_snippet(full_query_with_full_stops, special_result, nlp, url, source)
				elif len(rows) > 0 and rows[0]["_source"]["url"].startswith("https://microformats.org/wiki/"):
					url = rows[0]["_source"]["url"]
					source = rows[0]["_source"]

					do_i_use, special_result = search_result_features.generate_featured_snippet(full_query_with_full_stops, special_result, nlp, url, source)
				elif len(rows) > 0 and rows[0]["_source"]["url"].startswith("https://indieweb.org/"):
					url = rows[0]["_source"]["url"]
					source = rows[0]["_source"]

					do_i_use, special_result = search_result_features.generate_featured_snippet(full_query_with_full_stops, special_result, nlp, url, source)

				if "who is" in cleaned_value or ("." in cleaned_value and len(cleaned_value.split(".")[1]) <= 4) or cleaned_value.endswith("social") or cleaned_value.endswith("get rel") or cleaned_value.endswith("inspect feed"):
					get_homepage = session.get("https://es-indieweb-search.jamesg.blog/?pw={}&q={}&domain=true".format(config.ELASTICSEARCH_PASSWORD, cleaned_value_for_query.replace("who is", "").replace("get rel", "").replace("social", "").replace("inspect feed", ""))).json()

					if len(get_homepage.get("hits").get("hits")) > 0:
						url = get_homepage["hits"]["hits"][0]["_source"]["url"]
						source = get_homepage["hits"]["hits"][0]["_source"]

						# only do this if the first result is hosted on the domain the user queried
						if get_homepage["hits"]["hits"][0]["_source"].get("domain") and get_homepage["hits"]["hits"][0]["_source"]["domain"] == cleaned_value.split(" ")[0]:
							do_i_use, special_result = search_result_features.generate_featured_snippet(full_query_with_full_stops, special_result, nlp, url, source)

			if len(rows) == 0:
				out_of_bounds_page = True

				identify_mistakes = spell.unknown(cleaned_value.split('"')[-1].split(" "))

				final_query = ""

				suggestion = False

				cleaned_items = cleaned_value.split('"')[-1].split(" ")

				for w in range(0, len(cleaned_items)):
					if cleaned_items[w] in identify_mistakes and cleaned_items[w] != "":
						final_query += spell.correction(cleaned_items[w]) + " "
						suggestion = True

						final_query = " " + final_query
					else:
						final_query += cleaned_items[w] + " "

				final_query = "".join(cleaned_value.split('"')[:-1]) + '" ' + final_query
					
			else:
				out_of_bounds_page = False
				suggestion = False
				final_query = ""

			if "random aeropress" in cleaned_value or "generate aeropress" in cleaned_value and request.args.get("type") != "image":
				dose, grind_size, time, filters, water, stirring, stir_times, dose_is_point_five, inverted = search_result_features.aeropress_recipe()
				special_result = {
					"type": "aeropress_recipe",
					"dose": dose,
					"grind_size": grind_size,
					"time": time,
					"filters": filters,
					"water": water,
					"stirring": stirring,
					"stir_times": stir_times,
					"dose_is_point_five": dose_is_point_five,
					"inverted": inverted
				}

			if request.args.get("serp_as_json") and request.args.get("serp_as_json") == "direct":
				if special_result:
					return jsonify({"text": do_i_use, "featured_serp": special_result})
				else:
					return jsonify({"message": "no custom serp available on this search"})

			elif request.args.get("serp_as_json") and request.args.get("serp_as_json") == "results_page":
				return jsonify({"results": [r["_source"] for r in rows]})

			if request.args.get("type") == "image":
				base_results_query="/results?query={}&type=image".format(cleaned_value)
			else:
				base_results_query="/results?query={}".format(cleaned_value)

			if is_json:
				return jsonify(rows)

			# show one result if a featured snippet is available, even if there are no other results to show
			if special_result != False and do_i_use != None and int(num_of_results) == 0:
				num_of_results = 1
				out_of_bounds_page = False

			# bloggers = requests.get("https://es-indieweb-search.jamesg.blog/?pw={}&q={}&sort={}&from={}&to={}&discover=true".format(config.ELASTICSEARCH_PASSWORD, cleaned_value_for_query.replace("discover", "").strip(), order, str(pagination), str(int(pagination)+10))).json()

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
				# bloggers=bloggers["hits"]["hits"])
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

@main.route("/changelog")
def changelog():
	return render_template("changelog.html", title="IndieWeb Search Changelog")

@main.route("/advanced")
def advanced_search():
	count_request = requests.get("https://es-indieweb-search.jamesg.blog/count").json()

	count = count_request["es_count"]["count"]

	domains = count_request["domains"]

	return render_template("search/advanced_search.html", count=count, domains=domains, title="IndieWeb Search Advanced Search Options")

@main.route("/stats")
def stats():
	count_request = requests.get("https://es-indieweb-search.jamesg.blog/count").json()

	count = count_request["es_count"]["count"]

	domains = count_request["domains"]

	headers = {
		"Authorization": config.ELASTICSEARCH_API_TOKEN
	}

	feed_breakdown_request = requests.get("https://es-indieweb-search.jamesg.blog/feed_breakdown", headers=headers).json()

	special_stats = requests.get("https://es-indieweb-search.jamesg.blog/special_stats", headers=headers).json()

	top_linked_assets = special_stats["top_ten_links"]

	link_types = special_stats["link_microformat_instances"]

	return render_template("search/stats.html", count=count, domains=domains, title="IndieWeb Search Index Stats", feed_breakdown=feed_breakdown_request, top_linked_assets=top_linked_assets, link_types=link_types)

@main.route("/about")
def about():
	return render_template("search/about.html", title="About IndieWeb Search")