import json
import math
from dataclasses import asdict

import indieweb_utils
import mf2py
import requests
import spacy
from flask import (Blueprint, jsonify, redirect, render_template, request, session)

import config
import search.search_page_feeds as search_page_feeds
import search.transform_query as transform_query
from direct_answers import choose_direct_answer, search_result_features

main = Blueprint("main", __name__, static_folder="static", static_url_path="")

nlp = spacy.load("en_core_web_sm")

allowed_chars = [" ", '"', ":", "-", "/", ".", "=", ","]

def save_search_result_evaluation(evaluate: str, is_logged_in: bool, rows: list, cleaned_value_for_query: str) -> None:
    if evaluate == "save" and is_logged_in is True:
        get_ids_of_results = [r["_id"] for r in rows]

        relevance = request.args.get("relevance")

        # relevance as list
        relevance_list = relevance.split(",")

        count = 0

        results = []

        for id in get_ids_of_results:
            rank_object = {
                "_index": "pages",
                "_id": id,
                "rating": int(relevance_list[count])
            }

            count += 1

            results.append(rank_object)
        
        relevance_object = {
            "id": cleaned_value_for_query,
            "request": {
                "query": { "simple_query_string": { "query": cleaned_value_for_query, "minimum_should_match": "75%" } }
            },
            "ratings": results
        }

        with open("data/relevance.json", "a+") as f:
            f.write(json.dumps(relevance_object) + "\n")

def handle_random_query(session):
    random_site = session.get(
        "https://es-indieweb-search.jamesg.blog/random?pw={}".format(
            config.ELASTICSEARCH_PASSWORD
        )
    ).json()["domain"]

    return redirect(f"https://{random_site}/")


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
    ) = transform_query.get_clean_url_and_advanced_search(request, allowed_chars)

    if cleaned_value_for_query.startswith(
        "xray https://"
    ) or cleaned_value_for_query.startswith("xray http://"):
        return redirect(
            "https://xray.p3k.io/parse?url={}".format(
                cleaned_value_for_query.replace("xray ", "")
            )
        )

    app_session = requests.Session()

    if cleaned_value_for_query == "random":
        return handle_random_query(cleaned_value_for_query, app_session)

    if len(cleaned_value_for_query) == 0:
        return redirect("/")

    if session.get("me"):
        is_logged_in = True
    else:
        is_logged_in = False

    featured_serp_contents = ""

    pagination = "0"

    order, minimal, query_params = transform_query.parse_query_parameters(
        cleaned_value_for_query, query_values_in_list, request
    )

    rows = app_session.get(
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
        featured_serp_contents = choose_direct_answer.choose_featured_snippet(
            cleaned_value_for_query,
            cleaned_value_for_query,
            rows,
            full_query_with_full_stops,
            app_session,
            nlp,
        )
    if len(rows) == 0:
        out_of_bounds_page = True
        final_query = cleaned_value_for_query
    else:
        out_of_bounds_page = False
        final_query = ""

    if (
        "random aeropress" in cleaned_value_for_query
        or "generate aeropress" in cleaned_value_for_query
        and request.args.get("type") != "image"
    ):
        special_result = search_result_features.aeropress_recipe()

    # convert special_result to dict
    if special_result:
        special_result = asdict(special_result)

    special_format = search_page_feeds.process_special_format(
        request,
        rows,
        cleaned_value_for_query,
        page,
        special_result,
        featured_serp_contents,
    )

    print(featured_serp_contents)

    if special_format != None:
        return special_format

    # show one result if a featured snippet is available, even if there are no other results to show

    if not special_result and not featured_serp_contents and int(num_of_results) == 0:
        num_of_results = 0
        out_of_bounds_page = True
    else:
        out_of_bounds_page = False

    save_search_result_evaluation(request.args.get("evaluate"), is_logged_in, rows, cleaned_value_for_query)

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
        suggestion_made="",
        special_result=special_result,
        featured_serp_contents=featured_serp_contents,
        title=f"Search results for '{cleaned_value_for_query}' query",
        is_logged_in=is_logged_in
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
