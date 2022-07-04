import functools

import nltk
from bs4 import BeautifulSoup

from .structures import DirectAnswer


@functools.lru_cache()
def search_for_strong_memo(soup, cleaned_value):
    return [
        f
        for f in soup.find_all(["strong"])
        if any(x in f.text.lower() for x in cleaned_value.strip().split(" "))
    ]


def retrieve_answer(
    soup: BeautifulSoup,
    original_cleaned_value: str,
    cleaned_value: str,
    new_cleaned_value_for_direct_answer: str,
    post: dict,
    url: str,
) -> DirectAnswer:
    """
    Find an answer to a query in a post's text content.

    :param soup: BeautifulSoup object of the post's text content
    :param original_cleaned_value: The original cleaned value from the searcher's query
    :param cleaned_value: The cleaned value from the searcher's query
    :param new_cleaned_value_for_direct_answer: The cleaned value from the searcher's query
    :param post: The post object
    :param url: The URL of the post

    :return: A DirectAnswer object.
    :rtype: DirectAnswer
    """
    # initialize tokenizer for later use with nltk
    t = nltk.tokenize.WhitespaceTokenizer()

    c = nltk.text.Text(t.tokenize(soup.text))

    if not (
        len(original_cleaned_value) != 0
        and len(original_cleaned_value.split(" ")) > 0
        and "what is" in original_cleaned_value.lower()
    ):
        return None

    special_result = {}

    try:
        featured_serp_contents = c.concordance_list(cleaned_value, width=50)

        # check if in h2

        in_h2 = [
            f
            for f in soup.find_all(["h2", "h3"])
            if original_cleaned_value in f.text.lower()
        ]

        if len(in_h2) == 1:
            # get p after in_h2
            location_of_tag = in_h2[0]

            location_of_tag_final = ""

            for f in location_of_tag.find_next_siblings()[:3]:
                accepted_values = ["p", "li", "ul", "ol", "pre", "a"]
                not_accepted_values = ["h1", "h2", "h3", "h4", "h5", "h6"]

                if f.name in accepted_values and f.name not in not_accepted_values:
                    location_of_tag_final += str(f)
                else:
                    break

            html = f"<b>{in_h2[0].text}</b><br>{location_of_tag_final}"

            return DirectAnswer(
                answer_html=html,
                answer_type="direct_answer",
                breadcrumb=url,
                title=soup.find("h1").text,
                featured_image=post.get("featured_image"),
            )

        all_locations = [
            f
            for f in soup.find_all(["p"])
            if original_cleaned_value.lower() in f.text.lower()
            and (soup.next_sibling.name != "ul" or soup.next_sibling.name != "ol")
        ]

        location_of_tag = all_locations[0]

        if len(all_locations) > 0:
            featured_serp_contents = "<b>" + str(all_locations[0].text) + "</b>"

            return DirectAnswer(
                answer_html=featured_serp_contents,
                answer_type="direct_answer",
                breadcrumb=url,
                title=soup.find("h1").text,
                featured_image=post.get("featured_image"),
            )

        all_locations = [
            f for f in soup.find_all(["li"]) if original_cleaned_value in f.text.lower()
        ]

        if all_locations:
            location_of_tag = all_locations[0]
            position_in__parent_list = location_of_tag.find_parent().index(
                location_of_tag
            )
        elif len(in_h2) > 1:
            location_of_tag = in_h2[1]
            position_in__parent_list = location_of_tag.find_parent().index(
                location_of_tag
            )
        elif len((soup, new_cleaned_value_for_direct_answer)) > 0:
            position_in__parent_list = 0
            all_locations = soup.find_all(["h2"])
            location_of_tag = all_locations[0]
        elif len(search_for_strong_memo(soup, cleaned_value)) > 0:
            all_locations = search_for_strong_memo(soup, cleaned_value)
            location_of_tag = all_locations[0]

        if (
            location_of_tag.find_parent().name != "article"
            and location_of_tag.name == "li"
        ):
            # Show previous element for context and content addressing visitor query
            if position_in__parent_list - 2 < 0:
                start = 0
                add_ellipses = ""
            else:
                start = position_in__parent_list - 2
                add_ellipses = "<li>...</li>"

            all_lis = [
                str(i) for i in location_of_tag.find_parent().children if i.name == "li"
            ]
            first_five_children = all_lis[start : position_in__parent_list + 3]

            if len(all_lis) == 4:
                featured_serp_contents = (
                    str(location_of_tag.find_parent().find_previous())
                    + f"<{str(location_of_tag.find_parent().name)}>"
                    + "".join(all_lis)
                    + f"</{location_of_tag.find_parent().name}>"
                    + "<p>...</p>"
                )
            elif len(list(location_of_tag.find_parent().children)) > 5:
                featured_serp_contents = (
                    str(location_of_tag.find_parent().find_previous())
                    + f"<{str(location_of_tag.find_parent().name)}>"
                    + add_ellipses
                    + "".join(first_five_children)
                    + "<li>...</li>"
                    + f"</{location_of_tag.find_parent().name}>"
                )
            else:
                featured_serp_contents = (
                    str(location_of_tag.find_parent().find_previous())
                    + f"<{str(location_of_tag.find_parent().name)}>"
                    + "".join(first_five_children)
                    + f"</{location_of_tag.find_parent().name}>"
                )
        elif location_of_tag and (
            location_of_tag.name == "h2" or location_of_tag.name == "h3"
        ):
            featured_serp_contents = (
                "<ul>"
                + "".join([f"<li>{h2.text}</li>" for h2 in list(all_locations)])
                + "</ul>"
            )
        elif location_of_tag.name == "strong":
            featured_serp_contents = (
                "<b>"
                + str(location_of_tag.text)
                + "</b>"
                + str(location_of_tag.find_next())
            )
        elif location_of_tag.name == "p":
            sentence = [
                w.text for w in location_of_tag.split(". ") if cleaned_value in w.text
            ][0]
            featured_serp_contents = "<b>" + str(sentence) + "</b>"
        elif location_of_tag.find_parent().name != "article":
            featured_serp_contents = str(
                location_of_tag.find_parent().find_previous()
            ) + str(location_of_tag.find_parent())
        else:
            featured_serp_contents = ""

        if len(BeautifulSoup(featured_serp_contents, "lxml").get_text()) < 60:
            return None

        special_result = {
            "type": "direct_answer",
            "breadcrumb": url,
            "title": soup.find("h1").text,
            "featured_image": post.get("featured_image"),
        }
    except:
        featured_serp_contents = ""

    # Protect against direct answers that are too long
    if len(featured_serp_contents) > 400:
        featured_serp_contents = ""
        special_result = {}

    return DirectAnswer(
        answer_html=featured_serp_contents,
        answer_type=special_result.get("type", ""),
        breadcrumb=special_result.get("breadcrumb", ""),
        title=special_result.get("title", ""),
        featured_image=special_result.get("featured_image", ""),
    )
