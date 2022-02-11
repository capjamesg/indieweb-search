import datetime
import functools
import random

import nltk
from bs4 import BeautifulSoup

from . import entity_type_map as entity_types
from . import events, recipes, reviews, whatis, whois


@functools.lru_cache()
def search_for_h2_memo(soup, new_cleaned_value_for_direct_answer):
    return [
        f
        for f in soup.find_all(["h2"])
        if new_cleaned_value_for_direct_answer in f.text.lower()
    ]


@functools.lru_cache()
def search_for_strong_memo(soup, cleaned_value):
    return [
        f
        for f in soup.find_all(["strong"])
        if any(x in f.text.lower() for x in cleaned_value.strip().split(" "))
    ]


def generate_featured_snippet(
    cleaned_value, special_result, nlp, url=None, post=None, direct=False
):
    # Generate a featured snippet for the search result
    if url is None:
        return "", special_result

    original_url = url

    if "who is" in cleaned_value:
        url = url.replace("https://", "").replace("http://", "").split("/")[0]

    original_cleaned_value = cleaned_value.lower()

    new_cleaned_value_for_direct_answer = " ".join(
        [
            w
            for w in cleaned_value.split(" ")
            if w not in nltk.corpus.stopwords.words("english") or w in ["why", "how"]
        ]
    ).strip()

    # get post with home brew bar url

    proper_nouns = [
        word.lower()
        for word, pos in nltk.tag.pos_tag(post["title"].split())
        if pos == "NNP"
    ]

    # remove all proper nouns from cleaned_value

    cleaned_value = " ".join(
        [
            w
            for w in cleaned_value.split(" ")
            if w.lower() not in proper_nouns
            and w.lower() not in post["title"].lower().split()
            and w.lower() not in post["url"].lower().split("/")[-1]
        ]
    )

    # read post with bs4
    if post.get("page_content"):
        soup = BeautifulSoup(post["page_content"], "lxml")
    else:
        return "", special_result

    if "code" in original_cleaned_value or "markup" in original_cleaned_value:
        if "<pre>" or "<em>" in post["page_content"]:
            # get all pre tags

            pre_tags = soup.find_all("pre")

            for tag in pre_tags:
                # if paragraph before mentions term
                tag_before = tag.find_previous_sibling("p")
                # get tag before the last one
                if tag_before and tag_before.text:
                    tag_before_last = tag_before.find_previous_sibling("p")
                    heading_before = tag.find_previous_sibling("h2")
                    context = (
                        "<h2>"
                        + heading_before.text
                        + "</h2>"
                        + "<p>"
                        + tag_before_last.text
                        + "</p>"
                        + "<p>"
                        + tag_before.text
                        + "</p>"
                    )
                elif tag.text:
                    context = "<p>" + tag.text + "</p>"

                return tag.text, {
                    "url": original_url,
                    "title": post["title"],
                    "type": "code",
                    "breadcrumb": url,
                    "context": context,
                }

    all_locations = []

    featured_serp_contents, response = recipes.parse_recipe(
        original_cleaned_value, soup, url, post
    )

    if featured_serp_contents is not None and response is not None:
        return featured_serp_contents, response

    featured_serp_contents, response = reviews.parse_review(
        original_cleaned_value, soup, url, post
    )

    if featured_serp_contents is not None and response is not None:
        return featured_serp_contents, response

    featured_serp_contents, response = events.parse_event(
        original_cleaned_value, soup, url, post
    )

    if featured_serp_contents is not None and response is not None:
        return featured_serp_contents, response

    featured_serp_contents, response = whatis.parse_what_is(
        original_cleaned_value, soup, url, direct
    )

    if featured_serp_contents is not None and response is not None:
        return featured_serp_contents, response

    featured_serp_contents, response = whois.parse_whois(
        original_cleaned_value, soup, url, original_url
    )

    if featured_serp_contents is not None and response is not None:
        return featured_serp_contents, response

    featured_serp_contents, response = whois.parse_social(
        original_cleaned_value, soup, url, original_url
    )

    if featured_serp_contents is not None and response is not None:
        return featured_serp_contents, response

    featured_serp_contents, response = whois.parse_get_rel(
        original_cleaned_value, soup, original_url
    )

    if featured_serp_contents is not None and response is not None:
        return featured_serp_contents, response

    featured_serp_contents, response = whois.parse_feed(
        original_cleaned_value, soup, url, original_url
    )

    if featured_serp_contents is not None and response is not None:
        return featured_serp_contents, response

    featured_serp_contents, response = whois.parse_address(
        original_cleaned_value, soup, url, original_url
    )

    if featured_serp_contents is not None and response is not None:
        return featured_serp_contents, response

    # check if cleaned value refers to an ent type
    ent_type = "NONE"

    for word in cleaned_value.split(" "):
        if entity_types.get(word.lower()):
            ent_type = entity_types.get(word.lower())
            if ent_type == "GPE":
                all_locations = [
                    w
                    for w in nlp(
                        " ".join(soup.get_text().replace("\n", ". ").split(". "))
                    ).ents
                    if w.label_ == "GPE" and "in" in w.text
                ]
                if len(all_locations) > 0:
                    all_locations = all_locations[0]
            break

    if ent_type != "NONE":
        sentence_with_query = [
            s
            for s in soup.get_text().replace("\n", ". ").split(". ")
            if all(x in s.lower() for x in cleaned_value.strip().split(" "))
        ]

        if len(sentence_with_query) > 0:
            ents = [w for w in nlp(sentence_with_query[0]).ents if w.label_ == ent_type]

            if len(ents) > 0:
                return "<b style='font-size: 22px'>{}</b><br>{}".format(
                    ", ".join([e.text for e in ents]),
                    sentence_with_query[0].replace("\n", " "),
                ), {
                    "type": "direct_answer",
                    "breadcrumb": url,
                    "title": soup.find("h1").text,
                    "featured_image": post.get("featured_image"),
                }
            elif len(all_locations) > 0:
                return "<b style='font-size: 22px'>{}</b><br>{}".format(
                    all_locations[0].text, sentence_with_query[0]
                ), {
                    "type": "direct_answer",
                    "breadcrumb": url,
                    "title": soup.find("h1").text,
                    "featured_image": post.get("featured_image"),
                }

    # initialize tokenizer for later use with nltk
    t = nltk.tokenize.WhitespaceTokenizer()

    c = nltk.text.Text(t.tokenize(soup.text))

    # get definition if on page and same as query
    if soup.find_all("dfn"):
        for dfn in soup.find_all("dfn"):
            if (
                dfn.text.lower().replace(" ", "").replace("-", "")
                == new_cleaned_value_for_direct_answer.lower()
                .replace(" ", "")
                .replace("-", "")
                or "define" in new_cleaned_value_for_direct_answer.lower()
            ):

                return "<b style='font-size: 22px'>{}</b><br>{}".format(
                    dfn.text, dfn.find_parent("p").text
                ), {
                    "type": "direct_answer",
                    "breadcrumb": url,
                    "title": post["title"],
                    "featured_image": post.get("featured_image"),
                }

    if (
        len(original_cleaned_value) != 0
        and len(original_cleaned_value.split(" ")) > 0
        and "what is" in original_cleaned_value.lower()
    ):
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

                return f"<b>{in_h2[0].text}</b><br>{location_of_tag_final}", {
                    "type": "direct_answer",
                    "breadcrumb": url,
                    "title": soup.find("h1").text,
                    "featured_image": post.get("featured_image"),
                }

            all_locs = [
                f
                for f in soup.find_all(["p"])
                if original_cleaned_value.lower() in f.text.lower()
                and (soup.next_sibling.name != "ul" or soup.next_sibling.name != "ol")
            ]

            location_of_tag = all_locs[0]

            if len(all_locs) > 0:
                featured_serp_contents = "<b>" + str(all_locs[0].text) + "</b>"
                return featured_serp_contents, {
                    "type": "direct_answer",
                    "breadcrumb": url,
                    "title": soup.find("h1").text,
                    "featured_image": post.get("featured_image"),
                }

            all_locs = [
                f
                for f in soup.find_all(["li"])
                if original_cleaned_value in f.text.lower()
            ]

            if all_locs:
                location_of_tag = all_locs[0]
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
                all_locs = soup.find_all(["h2"])
                location_of_tag = all_locs[0]
            elif len(search_for_strong_memo(soup, cleaned_value)) > 0:
                all_locs = search_for_strong_memo(soup, cleaned_value)
                location_of_tag = all_locs[0]

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
                    str(i)
                    for i in location_of_tag.find_parent().children
                    if i.name == "li"
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
                    + "".join([f"<li>{h2.text}</li>" for h2 in list(all_locs)])
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
                    w.text
                    for w in location_of_tag.split(". ")
                    if cleaned_value in w.text
                ][0]
                featured_serp_contents = "<b>" + str(sentence) + "</b>"
            elif location_of_tag.find_parent().name != "article":
                featured_serp_contents = str(
                    location_of_tag.find_parent().find_previous()
                ) + str(location_of_tag.find_parent())
            else:
                featured_serp_contents = ""

            if len(BeautifulSoup(featured_serp_contents, "lxml").get_text()) < 60:
                return "", special_result

            special_result = {
                "type": "direct_answer",
                "breadcrumb": url,
                "title": soup.find("h1").text,
                "featured_image": post.get("featured_image"),
            }
        except:
            featured_serp_contents = ""
    else:
        featured_serp_contents = ""

    # Protect against direct answers that are too long
    if len(featured_serp_contents) > 400:
        featured_serp_contents = ""
        special_result = {}

    return featured_serp_contents, special_result


def aeropress_recipe():
    # Rounding helper function for timing

    def myround(x, base=5):
        result = base * round(x / base)
        if result == 10:
            result = 0
        return result

    # Generate brewing variables

    dose = random.randint(12, 16)

    dose_is_point_five = random.choice([True, False])

    inverted = random.choice([True, False])

    # 1 in 7 chance I get a "really coarse" recipe with a coarse grind and a long brew time
    type_is_really_coarse = random.randint(1, 7)

    if type_is_really_coarse == 1:
        grind_size = random.randint(24, 30)
        time_in_seconds = random.randint(180, 300)
    else:
        grind_size = random.randint(18, 24)
        time_in_seconds = random.randint(45, 150)

    time_long = str(datetime.timedelta(seconds=time_in_seconds))
    time = time_long.split(":", 1)[1]

    last_time_int = time[-1]
    last_time_first_three = time[:-1]
    last_time_rounded = str(myround(int(last_time_int)))

    time = last_time_first_three + last_time_rounded

    filters = random.randint(1, 2)
    water = "250"

    stir_times = random.randint(0, 6)

    stirring_options = [
        "before putting the cap on",
        "before pluging",
        "both before putting the cap on and before plunging",
    ]

    stirring = random.choice(stirring_options)

    special_result = {
        "type": "aeropress_recipe",
        "dose": dose,
        "grind_size": grind_size,
        "time": time,
        "filters": filters,
        "water": water,
        "stirring": stirring,
        "stir_times": stir_times,
        "dose_is_point_five": dose_is_point_five,
        "inverted": inverted,
    }

    return special_result
