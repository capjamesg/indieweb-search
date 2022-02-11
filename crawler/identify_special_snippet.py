from typing import Tuple

import mf2py


def find_snippet(page_content: str, h_card: dict) -> Tuple[dict, dict]:
    """
    Take h-entry object and see if it is eligible for a special h- snippet.

    :param h_card: h-card object

    :return: True if eligible, False otherwise
    """
    h_entry = mf2py.parse(page_content)

    special_snippet = {}

    for i in h_entry["items"]:
        if i["type"] == ["h-entry"]:
            if i["properties"] and i["properties"].get("author"):
                # if author is h_card
                if type(i["properties"]["author"][0]) == dict and i["properties"][
                    "author"
                ][0].get("type") == ["h-card"]:
                    h_card = i["properties"]["author"][0]

                elif type(i["properties"]["author"]) == list:
                    h_card = i["properties"]["author"][0]

        elif i["type"] == ["h-product"]:
            special_snippet = i
            break

        elif i["type"] == ["h-event"]:
            special_snippet = i
            break

        elif i["type"] == ["h-review"]:
            special_snippet = i
            break

        elif i["type"] == ["h-recipe"]:
            special_snippet = i
            break

    return special_snippet, h_card
