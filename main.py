import json
import math

import indieweb_utils
import mf2py
import requests
import spacy
from flask import (Blueprint, jsonify, redirect, render_template, request,
                   send_from_directory)

import config
import search.search_helpers as search_helpers
import search.search_page_feeds as search_page_feeds
from direct_answers import choose_direct_answer, search_result_features

main = Blueprint("main", __name__, static_folder="static", static_url_path="")

nlp = spacy.load("en_core_web_sm")

allowed_chars = [" ", '"', ":", "-", "/", ".", "=", ","]


def get_clean_url_and_advanced_search(request):
    query_with_handled_spaces = (
        request.args.get("query").replace("--", "").replace("  ", " ").strip()
    )

    cleaned_value_for_query = "".join(
        e for e in query_with_handled_spaces if e.isalnum() or e in allowed_chars
    ).strip()

    full_query_with_full_stops = "".join(
        e for e in query_with_handled_spaces if e.isalnum() or e == " " or e == "."
    )

    (
        query_values_in_list,
        query_with_handled_spaces,
    ) = search_helpers.handle_advanced_search(query_with_handled_spaces)

    return cleaned_value_for_query, full_query_with_full_stops, query_values_in_list


def handle_random_query(session):
    random_site = session.get(
        "https://es-indieweb-search.jamesg.blog/random?pw={}".format(
            config.ELASTICSEARCH_PASSWORD
        )
    ).json()["domain"]

    return redirect(f"https://{random_site}/")


def parse_query_parameters(cleaned_value_for_query, query_values_in_list):
    order = "score"
    minimal = "false"

    if request.args.get("order") == "date_asc":
        order = "date_asc"
    elif request.args.get("order") == "date_desc":
        order = "date_desc"

    cleaned_value_for_query = cleaned_value_for_query.replace("what is", "").lower()

    if request.args.get("format") and (
        request.args.get("format") == "json_feed" or request.args.get("format") == "jf2"
    ):
        minimal = "true"

    query_params = ""

    if query_values_in_list.get("site"):
        query_params += f"&site={query_values_in_list.get('site').replace('%', '')}"

    if request.args.get("query").startswith("discover"):
        query_params += "&discover=true"

    if "js:none" in request.args.get("query"):
        query_params += "&js=false"

    if query_values_in_list.get("category"):
        query_params += f"&category={query_values_in_list.get('category')}"

    if query_values_in_list.get("mf2prop"):
        query_params += f"&mf2_property={query_values_in_list.get('mf2prop')}"

    return order, minimal, query_params


def process_special_format(
    request, rows, cleaned_value, page, special_result, featured_serp_contents
):
    format = request.args.get("format")

    if format == "json_feed":
        json_feed = search_page_feeds.process_json_feed(
            rows, cleaned_value, page, format
        )

        return json_feed

    elif format == "jf2":
        jf2_feed = search_page_feeds.process_jf2_feed(rows)

        return jf2_feed

    elif format == "rss":
        rss_feed = search_page_feeds.process_rss_feed(rows, cleaned_value, page, format)

        return rss_feed

    elif format == "direct_serp_json":
        if special_result:
            return jsonify(
                {"text": featured_serp_contents, "featured_serp": special_result}
            )
        else:
            return jsonify({"message": "no custom serp available on this search"})

    elif format == "results_page_json":
        return jsonify({"results": [r["_source"] for r in rows]})


@main.route("/")
def home():
    q = request.args.get("q")
    return render_template("search/submit.html", title="IndieWeb Search", query=q)


@main.route("/autocomplete")
def search_autocomplete():
    query = request.args.get("q")
    suggest = requests.get(
        "https://es-indieweb-search.jamesg.blog/suggest?q={}&pw={}".format(
            query, config.ELASTICSEARCH_PASSWORD
        )
    )

    return jsonify(suggest.json()), 200


@main.route("/results", methods=["GET", "POST"])
def results_page():
    page = request.args.get("page")

    special_result = False

    if not request.args.get("query"):
        return redirect("/")

    if not page:
        page = 1

    if not str(page).isdigit():
        return redirect("/")

    if int(page) > 1:
        pagination = (int(page) - 1) * 10

    (
        cleaned_value_for_query,
        full_query_with_full_stops,
        query_values_in_list,
    ) = get_clean_url_and_advanced_search(request)

    if cleaned_value_for_query.startswith(
        "xray https://"
    ) or cleaned_value_for_query.startswith("xray http://"):
        return redirect(
            "https://xray.p3k.io/parse?url={}".format(
                cleaned_value_for_query.replace("xray ", "")
            )
        )

    session = requests.Session()

    if cleaned_value_for_query == "random":
        return handle_random_query(cleaned_value_for_query, session)

    if len(cleaned_value_for_query) == 0:
        return redirect("/")

    featured_serp_contents = ""

    pagination = "0"

    order, minimal, query_params = parse_query_parameters(
        cleaned_value_for_query, query_values_in_list
    )

    rows = session.get(
        "https://es-indieweb-search.jamesg.blog/?pw={}&q={}&sort={}&from={}&minimal={}{}".format(
            config.ELASTICSEARCH_PASSWORD,
            cleaned_value_for_query.replace("who is", "")
            .replace("code", "")
            .replace("discover ", "")
            .strip(),
            order,
            str(pagination),
            minimal,
            query_params,
        )
    ).json()

    num_of_results = rows["hits"]["total"]["value"]
    rows = rows["hits"]["hits"]

    for r in rows:
        if r["_source"].get("h_card"):
            r["_source"]["h_card"] = json.loads(r["_source"]["h_card"])
        else:
            r["_source"]["h_card"] = None

    # only page 1 is eligible to show a featured snippet
    if page == 1:
        (
            featured_serp_contents,
            special_result,
        ) = choose_direct_answer.choose_featured_snippet(
            cleaned_value_for_query,
            cleaned_value_for_query,
            rows,
            special_result,
            full_query_with_full_stops,
            session,
            nlp,
        )

    if len(rows) == 0:
        out_of_bounds_page = True
        final_query = cleaned_value_for_query
    else:
        out_of_bounds_page = False
        suggestion = False
        final_query = ""

    if (
        "random aeropress" in cleaned_value_for_query
        or "generate aeropress" in cleaned_value_for_query
        and request.args.get("type") != "image"
    ):
        special_result = search_result_features.aeropress_recipe()

    process_special_format(
        request,
        rows,
        cleaned_value_for_query,
        page,
        special_result,
        featured_serp_contents,
    )

    # show one result if a featured snippet is available, even if there are no other results to show

    if not special_result and not featured_serp_contents and int(num_of_results) == 0:
        num_of_results = 0
        out_of_bounds_page = True
    else:
        out_of_bounds_page = False

    return render_template(
        "search/results.html",
        results=rows,
        number_of_results=int(num_of_results),
        page=int(page),
        page_count=int(math.ceil(num_of_results / 10)),
        query=cleaned_value_for_query,
        results_type=request.args.get("type"),
        out_of_bounds_page=out_of_bounds_page,
        ordered_by=request.args.get("order"),
        base_results_query="/results?query=" + cleaned_value_for_query,
        corrected_text=final_query,
        suggestion_made=suggestion,
        special_result=special_result,
        featured_serp_contents=featured_serp_contents,
        title=f"Search results for '{cleaned_value_for_query}' query",
    )


@main.route("/robots.txt")
def robots():
    return send_from_directory(main.static_folder, "robots.txt")


@main.route("/assets/<path:path>")
def send_static_images(path):
    return send_from_directory("static/", path)


@main.route("/changelog")
def changelog():
    return render_template("changelog.html", title="IndieWeb Search Changelog")


@main.route("/advanced")
def advanced_search():
    return render_template(
        "search/advanced_search.html", title="IndieWeb Search Advanced Search Options"
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
        return jsonify(
            {
                "status": "failed",
                "message": "No microformats could be found on this page",
                "author": [],
            }
        )

    if not mf2_parsed["items"]:
        return jsonify(
            {
                "status": "failed",
                "message": "No microformats could be found on this page",
                "author": [],
            }
        )

    # get h_entry
    h_entry = [i for i in mf2_parsed["items"] if i["type"] == ["h-entry"]]

    h_card = [i for i in mf2_parsed["items"] if i["type"] == ["h-card"]]

    if not h_entry and h_card == []:
        return jsonify(
            {
                "status": "failed",
                "message": "No h-entry could be found on this page",
                "author": [],
            }
        )

    if h_card == []:
        for i in h_entry["items"]:
            if i["type"] == ["h-entry"]:
                if i["properties"].get("author"):
                    # if author is h_card
                    if type(i["properties"]["author"][0]) == dict and i["properties"][
                        "author"
                    ][0].get("type") == ["h-card"]:
                        h_card = i["properties"]["author"][0]

                    elif type(i["properties"]["author"]) == list:
                        h_card = i["properties"]["author"][0]

    result = indieweb_utils.discover_author(h_card, h_entry, page_to_check, [])

    return jsonify({"status": "success", "result": result})


@main.route("/stats")
def stats():
    count_request = requests.get("https://es-indieweb-search.jamesg.blog/count").json()

    count = count_request["es_count"]["count"]

    domains = count_request["domains"]

    headers = {"Authorization": config.ELASTICSEARCH_API_TOKEN}

    feed_breakdown_request = requests.get(
        "https://es-indieweb-search.jamesg.blog/feed_breakdown", headers=headers
    ).json()

    special_stats = requests.get(
        "https://es-indieweb-search.jamesg.blog/special_stats", headers=headers
    ).json()

    top_linked_assets = special_stats["top_ten_links"]

    link_types = special_stats["link_microformat_instances"]

    return render_template(
        "search/stats.html",
        count=count,
        domains=domains,
        title="IndieWeb Search Index Stats",
        feed_breakdown=feed_breakdown_request,
        top_linked_assets=top_linked_assets,
        link_types=link_types,
    )


@main.route("/about")
def about():
    return render_template("search/about.html", title="About IndieWeb Search")
