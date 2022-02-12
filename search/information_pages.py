import requests
from flask import Blueprint, render_template

import config

information_pages = Blueprint(
    "information_pages", __name__, static_folder="static", static_url_path=""
)


@information_pages.route("/stats")
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


@information_pages.route("/about")
def about():
    return render_template("search/about.html", title="About IndieWeb Search")


@information_pages.route("/changelog")
def changelog():
    return render_template("changelog.html", title="IndieWeb Search Changelog")


@information_pages.route("/advanced")
def advanced_search():
    return render_template(
        "search/advanced_search.html", title="IndieWeb Search Advanced Search Options"
    )
