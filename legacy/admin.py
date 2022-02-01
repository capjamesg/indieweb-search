import csv
import json
import sqlite3

from flask import Blueprint, render_template, request
from flask_login import current_user, login_required

# from . import db
# from .models import User
from .config import ROOT_DIRECTORY

admin = Blueprint("admin", __name__, static_folder="static", static_url_path="")


@admin.route("/log", methods=["GET", "POST"])
def show_indexing_log():
    issue_search = request.args.get("issue_search")

    connection = sqlite3.connect(ROOT_DIRECTORY + "/search.db")

    with connection:
        cursor = connection.cursor()
        if issue_search and issue_search != "all":
            index_status = cursor.execute(
                "SELECT * FROM crawl_errors where message = ?;", (issue_search,)
            ).fetchall()
        else:
            issue_search = None
            index_status = cursor.execute(
                "SELECT * FROM crawl_errors ORDER BY message;"
            ).fetchall()

        with open(ROOT_DIRECTORY + "/static/index_stats.json", "r") as f:
            index_stats = json.load(f)

        issue_breakdown = cursor.execute(
            "SELECT COUNT(url), message FROM crawl_errors GROUP BY message;"
        ).fetchall()

        unique_error_types = cursor.execute(
            "SELECT DISTINCT message FROM crawl_errors;"
        ).fetchall()

        return render_template(
            "admin/index_log.html",
            results=index_status,
            index_stats=index_stats,
            unique_error_types=unique_error_types,
            issue_search=issue_search,
            issue_breakdown=issue_breakdown,
            page="log",
            title="Search Index Log",
        )


@admin.route("/log/test-queries")
@login_required
def show_test_queries():
    with open(ROOT_DIRECTORY + "/data/test_queries.md", "r") as f:
        test_queries = f.readlines()

    with open(ROOT_DIRECTORY + "/static/index_stats.json", "r") as f:
        index_stats = json.load(f)

    return render_template(
        "admin/test_queries.html",
        test_queries=test_queries,
        index_stats=index_stats,
        page="test-queries",
        title="Indexing Test Query Results | Search Dashboard",
    )


@admin.route("/log/past-crawls")
@login_required
def show_past_crawls():
    with open(ROOT_DIRECTORY + "/data/index_stats.csv", "r") as f:
        data = csv.reader(f)

        past_indexes = [d for d in data]

    return render_template(
        "admin/past_indexes.html",
        past_indexes=past_indexes,
        page="past-crawls",
        title="Past Crawl Logs | Search Dashboard",
    )


@admin.route("/log/crawl-charts")
@login_required
def show_index_log_charts():
    with open(ROOT_DIRECTORY + "/static/index_stats.json", "r") as f:
        index_stats = json.load(f)

    return render_template(
        "admin/charts.html",
        index_stats=index_stats,
        page="crawl-charts",
        title="Crawl Charts | Search Dashboard",
    )


@admin.route("/log/sitemaps")
@login_required
def show_crawled_sitemaps():
    with open(ROOT_DIRECTORY + "/static/index_stats.json", "r") as f:
        index_stats = json.load(f)

    # get sitemap
    connection = sqlite3.connect(ROOT_DIRECTORY + "/search.db")

    with connection:
        cursor = connection.cursor()

        sitemaps = cursor.execute("SELECT * FROM sitemaps;").fetchall()

    return render_template(
        "admin/sitemaps.html",
        sitemaps=sitemaps,
        index_stats=index_stats,
        page="sitemaps",
        title="Sitemaps Crawled | Search Dashboard",
    )
