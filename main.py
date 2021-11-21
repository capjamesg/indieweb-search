from flask import render_template, request, redirect, send_from_directory, jsonify, Blueprint
from .direct_answers import choose_direct_answer
from .direct_answers import search_result_features
from spellchecker import SpellChecker
from . import search_helpers, config, search_page_feeds
import requests
import json
import math
import spacy

main = Blueprint("main", __name__, static_folder="static", static_url_path="")

spell = SpellChecker()

nlp = spacy.load('en_core_web_sm')

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
	site = request.args.get("site")

	if site and site == "jamesg.blog":
		# used for special jamesg.blog search redirect, not for open use
		site = "".join([x for x in site if x.isalpha() or x == "."])

		return redirect('/results?query=site:"{}"%20{}'.format(site, request.args.get("query")))

	special_result = False

	if not request.args.get("query"):
		return redirect("/")

	query_with_handled_spaces = request.args.get("query").replace("--", "").replace("  ", " ").strip()

	allowed_chars = [" ", '"', ":", "-", "/", ".", "="]

	query_values_in_list, query_with_handled_spaces = search_helpers.handle_advanced_search(query_with_handled_spaces)

	cleaned_value_for_query = ''.join(e for e in query_with_handled_spaces if e.isalnum() or e in allowed_chars).strip()

	if cleaned_value_for_query.startswith("xray https://") or cleaned_value_for_query.startswith("xray http://"):
		return redirect("https://xray.p3k.io/parse?url={}".format(cleaned_value_for_query.replace("xray ", "")))

	session = requests.Session()

	if cleaned_value_for_query == "random":
		random_site = session.get("https://es-indieweb-search.jamesg.blog/random?pw={}".format(config.ELASTICSEARCH_PASSWORD)).json()["domain"]

		return redirect("https://{}/".format(random_site))

	if not request.args.get("query"):
		return redirect("/")

	full_query_with_full_stops = ''.join(e for e in query_with_handled_spaces if e.isalnum() or e == " " or e == ".")

	if len(cleaned_value_for_query) == 0:
		return redirect("/")

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

	order = "score"
	minimal = "false"

	if request.args.get("order") == "date_asc":
		order = "date_asc"
	elif request.args.get("order") == "date_desc":
		order = "date_desc"

	cleaned_value_for_query = cleaned_value_for_query.replace("what is", "")

	if request.args.get("format") and (request.args.get("format") == "json_feed" or request.args.get("format") == "jf2"):
		minimal = "true"

	query_params = ""
	
	if "site:" in request.args.get("query"):
		query_params += "&site={}".format(query_values_in_list[-1].replace("%", ""))

	if request.args.get("query").startswith("discover"):
		query_params += "&discover=true"

	if "js:none" in request.args.get("query"):
		query_params += "&js=false"
	
	rows = session.get("https://es-indieweb-search.jamesg.blog/?pw={}&q={}&sort={}&from={}&minimal={}{}".format(
		config.ELASTICSEARCH_PASSWORD,
		cleaned_value_for_query.replace("who is", "").replace("code", "").strip(),
		order, str(pagination),
		minimal,
		query_params)).json()

	num_of_results = rows["hits"]["total"]["value"]
	rows = rows["hits"]["hits"]

	for r in rows:
		if r["_source"].get("h_card"):
			r["_source"]["h_card"] = json.loads(r["_source"]["h_card"])
		else:
			r["_source"]["h_card"] = None
	
	if page == 1:
		cleaned_value = cleaned_value_for_query.lower()
		do_i_use, special_result = choose_direct_answer.choose_featured_snippet(
			cleaned_value,
			cleaned_value_for_query,
			rows,
			special_result,
			full_query_with_full_stops,
			session,
			nlp
		)

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
		special_result = search_result_features.aeropress_recipe()
		
	format = request.args.get("format")

	if format == "json_feed":
		json_feed = search_page_feeds.process_json_feed(rows, cleaned_value, page, format)

		return json_feed

	elif format == "jf2":
		jf2_feed = search_page_feeds.process_jf2_feed(rows)

		return jf2_feed

	elif format == "direct_serp_json":
		if special_result:
			return jsonify({"text": do_i_use, "featured_serp": special_result})
		else:
			return jsonify({"message": "no custom serp available on this search"})

	elif format == "results_page_json":
		return jsonify({"results": [r["_source"] for r in rows]})

	# show one result if a featured snippet is available, even if there are no other results to show
	if special_result != False and do_i_use != None and int(num_of_results) == 0:
		num_of_results = 1
		out_of_bounds_page = False

	return render_template("search/results.html",
		results=rows,
		number_of_results=int(num_of_results),
		page=int(page),
		page_count=int(math.ceil(num_of_results / 10)),
		query=cleaned_value,
		results_type=request.args.get("type"),
		out_of_bounds_page=out_of_bounds_page,
		ordered_by=request.args.get("order"),
		base_results_query=cleaned_value_for_query,
		corrected_text=final_query,
		suggestion_made=suggestion,
		special_result=special_result,
		do_i_use=do_i_use,
		title="Search results for '{}' query".format(cleaned_value))

@main.route("/robots.txt")
def robots():
	return send_from_directory(main.static_folder, "robots.txt")

@main.route('/assets/<path:path>')
def send_static_images(path):
	return send_from_directory("static/", path)

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