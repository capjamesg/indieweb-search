from typing import List

from flask import request

from . import search_helpers


def get_clean_url_and_advanced_search(
    request: request, allowed_chars: list
) -> List[list]:
    query_with_handled_spaces = (
        request.args.get("query").replace("--", "").replace("  ", " ").strip()
    )

    cleaned_value_for_query = (
        "".join(
            e for e in query_with_handled_spaces if e.isalnum() or e in allowed_chars
        )
        .strip()
        .lower()
    )

    full_query_with_full_stops = "".join(
        e for e in query_with_handled_spaces if e.isalnum() or e == " " or e == "."
    )

    (
        query_values_in_list,
        query_with_handled_spaces,
    ) = search_helpers.handle_advanced_search(query_with_handled_spaces)

    return cleaned_value_for_query, full_query_with_full_stops, query_values_in_list


def parse_query_parameters(
    cleaned_value_for_query: str, query_values_in_list: list, request: request
) -> List[list]:
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
