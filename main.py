from flask import render_template, request, redirect, send_from_directory, jsonify, Blueprint
from direct_answers import choose_direct_answer
from direct_answers import search_result_features
import indieweb_utils
import search_helpers, config, search_page_feeds
import requests
import json
import math
import spacy
import mf2py

main = Blueprint("main", __name__, static_folder="static", static_url_path="")

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

	allowed_chars = [" ", '"', ":", "-", "/", ".", "=", ","]

	cleaned_value_for_query = ''.join(e for e in query_with_handled_spaces if e.isalnum() or e in allowed_chars).strip()

	query_values_in_list, query_with_handled_spaces = search_helpers.handle_advanced_search(query_with_handled_spaces)

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
	
	if query_values_in_list.get("site"):
		query_params += "&site={}".format(query_values_in_list.get("site").replace("%", ""))

	if request.args.get("query").startswith("discover"):
		query_params += "&discover=true"

	if "js:none" in request.args.get("query"):
		query_params += "&js=false"

	if query_values_in_list.get("category"):
		query_params += "&category={}".format(query_values_in_list.get("category"))

	if query_values_in_list.get("mf2prop"):
		query_params += "&mf2_property={}".format(query_values_in_list.get("mf2prop"))
	
	rows = session.get("https://es-indieweb-search.jamesg.blog/?pw={}&q={}&sort={}&from={}&minimal={}{}".format(
		config.ELASTICSEARCH_PASSWORD,
		cleaned_value_for_query.replace("who is", "").replace("code", "").replace("discover ", "").strip(),
		order, str(pagination),
		minimal,
		query_params)
	).json()

	num_of_results = rows["hits"]["total"]["value"]
	rows = rows["hits"]["hits"]

	for r in rows:
		if r["_source"].get("h_card"):
			r["_source"]["h_card"] = json.loads(r["_source"]["h_card"])
		else:
			r["_source"]["h_card"] = None
			
	cleaned_value = cleaned_value_for_query.lower()
	
	if page == 1:
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
		final_query = cleaned_value_for_query

		# this code doesn't work right now

		# identify_mistakes = spell.unknown(cleaned_value.split('"')[-1].split(" "))

		# final_query = ""

		# suggestion = False

		# cleaned_items = cleaned_value.split('"')[-1].split(" ")

		# for w in range(0, len(cleaned_items)):
		# 	if cleaned_items[w] in identify_mistakes and cleaned_items[w] != "":
		# 		final_query += spell.correction(cleaned_items[w]) + " "
		# 		suggestion = True

		# 		final_query = " " + final_query
		# 	else:
		# 		final_query += cleaned_items[w] + " "

		# final_query = "".join(cleaned_value.split('"')[:-1]) + '" ' + final_query
			
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

	elif format == "rss":
		rss_feed = search_page_feeds.process_rss_feed(rows, cleaned_value, page, format)

		return rss_feed

	elif format == "direct_serp_json":
		if special_result:
			return jsonify({"text": do_i_use, "featured_serp": special_result})
		else:
			return jsonify({"message": "no custom serp available on this search"})

	elif format == "results_page_json":
		return jsonify({"results": [r["_source"] for r in rows]})

	# show one result if a featured snippet is available, even if there are no other results to show

	if not special_result and not do_i_use and int(num_of_results) == 0:
		num_of_results = 0
		out_of_bounds_page = True
	else:
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
		base_results_query="/results?query=" + cleaned_value_for_query,
		corrected_text=final_query,
		suggestion_made=suggestion,
		special_result=special_result,
		do_i_use=do_i_use,
		title="Search results for '{}' query".format(cleaned_value)
	)

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
	return render_template(
		"search/advanced_search.html",
		title="IndieWeb Search Advanced Search Options"
	)

@main.route("/api/post-type")
def get_original_post_type():
	page_to_check = request.args.get("url")

	mf2_parsed = mf2py.parse(page_to_check)

	if not mf2_parsed:
		return jsonify({"status": "failed", "result": ""})
	
	if not mf2_parsed["items"]:
		return jsonify({"status": "failed", "result": ""})

	# get h_entry
	h_entry = [i for i in mf2_parsed["items"] if i["type"] == ["h-entry"]]

	result = indieweb_utils.get_post_type(h_entry)

	return jsonify({"status": "success", "result": result})

@main.route("/api/authorship")
def get_post_author():
	page_to_check = request.args.get("url")

	mf2_parsed = mf2py.parse(page_to_check)

	if not mf2_parsed:
		return jsonify({"status": "failed", "message": "No microformats could be found on this page", "author": []})
	
	if not mf2_parsed["items"]:
		return jsonify({"status": "failed", "message": "No microformats could be found on this page", "author": []})

	# get h_entry
	h_entry = [i for i in mf2_parsed["items"] if i["type"] == ["h-entry"]]

	h_card = [i for i in mf2_parsed["items"] if i["type"] == ["h-card"]]

	if not h_entry and h_card == []:
		return jsonify({"status": "failed", "message": "No h-entry could be found on this page", "author": []})

	if h_card == []:
		for i in h_entry["items"]:
			if i['type'] == ['h-entry']:
				if i['properties'].get('author'):
					# if author is h_card
					if type(i['properties']['author'][0]) == dict and i['properties']['author'][0].get('type') == ['h-card']:
						h_card = i['properties']['author'][0]

					elif type(i['properties']['author']) == list:
						h_card = i['properties']['author'][0]

	result = indieweb_utils.discover_author(h_card, h_entry, page_to_check, [])

	return jsonify({"status": "success", "result": result})

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

	return render_template(
		"search/stats.html",
		count=count,
		domains=domains,
		title="IndieWeb Search Index Stats",
		feed_breakdown=feed_breakdown_request,
		top_linked_assets=top_linked_assets,
		link_types=link_types
	)

@main.route("/about")
def about():
	return render_template("search/about.html", title="About IndieWeb Search")