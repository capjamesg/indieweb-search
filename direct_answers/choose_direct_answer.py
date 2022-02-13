from urllib.parse import urlparse as parse_url

import requests
import spacy

import config

from . import search_result_features
from .entity_type_map import keyword_values
from .structures import DirectAnswer


def choose_featured_snippet(
    cleaned_value: str,
    cleaned_value_for_query: str,
    rows: list,
    full_query_with_full_stops: list,
    session: requests.Session,
    nlp: spacy,
) -> DirectAnswer:
    """
    Choose the snippet that is most relevant to the search term.
    """

    search_for_snippet = False

    featured_serp_contents = ""
    special_result = {}

    query_divided = cleaned_value_for_query.split(" ")

    for w in query_divided:
        if w in keyword_values:
            search_for_snippet = True

    parsed_url = parse_url(rows[0]["_source"]["url"])

    domain = parsed_url.netloc

    if search_for_snippet:
        # remove stopwords from query
        original = cleaned_value_for_query
        cleaned_value_for_query = (
            cleaned_value.replace("what is", "")
            .replace("code", "")
            .replace("markup", "")
            .replace("what are", "")
            .replace("why", "")
            .replace("how", "")
            .replace("what were", "")
            .replace("to use", "")
            .strip()
        )

        wiki_direct_result = [
            item
            for item in rows
            if domain == "indieweb.org"
            and "/" not in item["_source"]["title"]
            and cleaned_value_for_query.lower().strip()
            in item["_source"]["title"].lower()
        ]

        microformats_wiki_direct_result = [
            item
            for item in rows
            if domain == "microformats.org"
            and "/" not in item["_source"]["title"]
            and cleaned_value_for_query.lower() in item["_source"]["title"].lower()
        ]

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

        (
            featured_serp_contents,
            special_result,
        ) = search_result_features.generate_featured_snippet(
            original, special_result, nlp, url, source
        )

        if featured_serp_contents == "" and len(rows) > 1:
            (
                featured_serp_contents,
                special_result,
            ) = search_result_features.generate_featured_snippet(
                original,
                special_result,
                nlp,
                rows[1]["_source"]["url"],
                rows[1]["_source"],
            )

    elif len(rows) > 0 and (domain == "microformats.org" or domain == "indieweb.org"):
        url = rows[0]["_source"]["url"]
        source = rows[0]["_source"]

        (
            featured_serp_contents,
            special_result,
        ) = search_result_features.generate_featured_snippet(
            full_query_with_full_stops, special_result, nlp, url, source
        )

    if (
        "who is" in cleaned_value
        or ("." in cleaned_value and len(cleaned_value.split(".")[1]) <= 4)
        or cleaned_value.endswith("social")
        or cleaned_value.endswith("get rel")
        or cleaned_value.endswith("inspect feed")
    ):
        get_homepage = session.get(
            "https://es-indieweb-search.jamesg.blog/?pw={}&q={}&domain=true".format(
                config.ELASTICSEARCH_PASSWORD,
                cleaned_value_for_query.replace("who is", "")
                .replace("get rel", "")
                .replace("social", "")
                .replace("inspect feed", ""),
            )
        ).json()

        if len(get_homepage.get("hits").get("hits")) > 0:
            url = get_homepage["hits"]["hits"][0]["_source"]["url"]
            source = get_homepage["hits"]["hits"][0]["_source"]

            # only do this if the first result is hosted on the domain the user queried
            if (
                get_homepage["hits"]["hits"][0]["_source"].get("domain")
                and get_homepage["hits"]["hits"][0]["_source"]["domain"]
                == cleaned_value.split(" ")[0]
            ):
                (
                    featured_serp_contents,
                    special_result,
                ) = search_result_features.generate_featured_snippet(
                    full_query_with_full_stops, special_result, nlp, url, source
                )

    return featured_serp_contents, special_result
