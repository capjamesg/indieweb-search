import datetime
from typing import Tuple

from bs4 import BeautifulSoup


def get_page_info(
    page_html_contents: BeautifulSoup, page_url: str, homepage_meta_description: str
) -> Tuple[str, str, str, bool]:
    """
    Scrapes page information for index and returns it to be added to the index later.

    :param page_html_contents: The BeautifulSoup object of the HTML page
    :type page_html_contents: BeautifulSoup
    :param page_url: The full URL of the page on which the feed was found
    :type page_url: str
    :param homepage_meta_description: The meta description of the homepage
    :type homepage_meta_description: str
    """

    contains_hfeed = page_html_contents.find(class_="h-feed")

    if contains_hfeed:
        # get all h-entry elements
        h_entries = contains_hfeed.find_all(class_="h-entry")

        if len(h_entries) > 5 and page_url.count("/") > 4:
            return [], "", "", True

        # get date of first hentry
        if len(h_entries) > 0:
            first_hentry_date = h_entries[0].find(class_="dt-published")

            if first_hentry_date and first_hentry_date.get("datetime"):
                # if published before 3 weeks ago
                if (
                    first_hentry_date.get("datetime")
                    < (
                        datetime.datetime.now() - datetime.timedelta(weeks=3)
                    ).isoformat()
                    and page_url.count("/") > 3
                ):
                    return (
                        first_hentry_date.get("datetime"),
                        "",
                        "",
                        True,
                    )

    published_on = page_html_contents.find("time", attrs={"class": "dt-published"})

    if published_on and published_on.get("datetime") is not None:
        published_on = published_on["datetime"].split("T")[0]
    else:
        published_on = ""

    meta_description = ""

    properties_to_check = (
        ("name", "description"),
        ("name", "og:description"),
        ("property", "og:description"),
        ("name", "twitter:description"),
    )

    for key, value in properties_to_check:
        if (
            page_html_contents.find("meta", {key: value}) is not None
            and page_html_contents.find("meta", {key: value}).get("content")
            and page_html_contents.find("meta", {key: value})["content"] != ""
        ):
            meta_description = page_html_contents.find("meta", {key: value})["content"]
            break

    if meta_description == "" or (
        homepage_meta_description != ""
        and meta_description == homepage_meta_description
    ):
        summary = page_html_contents.select("p-summary")

        if summary:
            meta_description = summary[0].text

    # try to retrieve a larger meta description
    if (
        meta_description == ""
        or len(meta_description) < 75
        or (
            homepage_meta_description != ""
            and meta_description == homepage_meta_description
        )
    ):
        # Use first paragraph as meta description if one can be found
        # get paragraph after h1

        e_content = page_html_contents.find(class_="e-content")

        if e_content and len(e_content) > 0:
            potential_meta_description = e_content.find_all("p")
            if potential_meta_description and len(potential_meta_description) > 0:
                meta_description = potential_meta_description[0].text
                if len(meta_description) < 50:
                    meta_description = ""

    if (
        meta_description == ""
        or meta_description is None
        or len(meta_description) < 75
        or (
            homepage_meta_description != ""
            and meta_description == homepage_meta_description
        )
    ):
        h1 = page_html_contents.find("h1")

        if h1:
            paragraph_to_use_for_meta_desc = h1.find_next("p")

            if (
                paragraph_to_use_for_meta_desc
                and len(paragraph_to_use_for_meta_desc.text) < 50
            ):
                paragraph_to_use_for_meta_desc = h1.find_next("p").find_next("p")
                if paragraph_to_use_for_meta_desc:
                    meta_description = paragraph_to_use_for_meta_desc.text
            elif paragraph_to_use_for_meta_desc:
                meta_description = paragraph_to_use_for_meta_desc.text

    if (
        meta_description == ""
        or meta_description is None
        or (
            homepage_meta_description != ""
            and meta_description == homepage_meta_description
        )
    ):
        h2 = page_html_contents.find_all("h2")

        if h2 and len(h2) > 0:
            paragraph_to_use_for_meta_desc = h2[0].find_next("p")
            if paragraph_to_use_for_meta_desc is not None:
                meta_description = paragraph_to_use_for_meta_desc.text

    if meta_description is None:
        meta_description = ""

    # do not index stub descriptions from the IndieWeb wiki

    if meta_description.startswith("This article is a stub.") or (
        homepage_meta_description != ""
        and meta_description == homepage_meta_description
    ):
        stub = [p for p in page_html_contents.find_all("p") if "stub" in p.text]

        if stub:
            stub = [0]

            # get element after stub
            meta_description = " ".join(stub.find_next_sibling().text.split(" ")[:50])

    final_meta_description = ""
    char_count = 0

    for w in meta_description.split(" "):
        char_count += len(w)
        final_meta_description += w + " "

        if char_count > 180:
            final_meta_description += "..."
            break

    final_meta_description = BeautifulSoup(final_meta_description, "lxml").text

    if page_html_contents.find("title") is not None:
        doc_title = page_html_contents.find("title").text
    elif page_html_contents.find("h1") is not None:
        doc_title = page_html_contents.find("h1").text
    else:
        doc_title = page_url

    # use p-name in place of title tag if one is available
    if page_html_contents.select(".p-name"):
        doc_title = page_html_contents.select(".p-name")[0].text

    if doc_title == "":
        doc_title = page_url

    return (
        published_on,
        final_meta_description,
        doc_title,
        False,
    )
