import datetime

from bs4 import BeautifulSoup
from nltk.corpus import stopwords
from textblob import WordList

stopwords = set(stopwords.words("english"))

# Add the words below to the stopwords set
excluded_words = {
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
    "James",
    "every",
    "people",
    "thing",
    "first",
}

stopwords.update(excluded_words)

full_stopwords_list = {}

for word in stopwords:
    full_stopwords_list[word] = ""


def get_page_info(page_text, page_desc_soup, page_url, homepage_meta_description):
    """
    Scrapes page information for index and returns it to be added to the index later.

    :param page_text: The text on a web page
    :param page_desc_soup: The BeautifulSoup object of the HTML page
    :param page_url: The full URL of the page on which the feed was found
    :param homepage_meta_description: The meta description of the homepage
    """

    contains_hfeed = page_desc_soup.find(class_="h-feed")

    if contains_hfeed:
        # get all h-entry elements
        h_entries = contains_hfeed.find_all(class_="h-entry")

        if len(h_entries) > 5 and page_url.count("/") > 4:
            return page_text, page_desc_soup, [], "", "", True

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
                        page_text,
                        page_desc_soup,
                        first_hentry_date.get("datetime"),
                        "",
                        "",
                        True,
                    )

    published_on = page_desc_soup.find("time", attrs={"class": "dt-published"})

    meta_description = ""

    properties_to_check = [
        ("name", "description"),
        ("name", "og:description"),
        ("property", "og:description"),
        ("name", "twitter:description"),
    ]

    for key, value in properties_to_check:
        if (
            page_desc_soup.find("meta", {key: value}) != None
            and page_desc_soup.find("meta", {key: value}).get("content")
            and page_desc_soup.find("meta", {key: value})["content"] != ""
        ):
            meta_description = page_desc_soup.find("meta", {key: value})["content"]
            break

    if meta_description == "" or (
        homepage_meta_description != ""
        and meta_description == homepage_meta_description
    ):
        summary = page_desc_soup.select("p-summary")

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

        e_content = page_desc_soup.find(class_="e-content")

        if e_content and len(e_content) > 0:
            potential_meta_description = e_content.find_all("p")
            if potential_meta_description and len(potential_meta_description) > 0:
                meta_description = potential_meta_description[0].text
                if len(meta_description) < 50:
                    meta_description = ""

    if (
        meta_description == ""
        or meta_description == None
        or len(meta_description) < 75
        or (
            homepage_meta_description != ""
            and meta_description == homepage_meta_description
        )
    ):
        h1 = page_desc_soup.find("h1")

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
        or meta_description == None
        or (
            homepage_meta_description != ""
            and meta_description == homepage_meta_description
        )
    ):
        h2 = page_desc_soup.find_all("h2")

        if h2 and len(h2) > 0:
            paragraph_to_use_for_meta_desc = h2[0].find_next("p")
            if paragraph_to_use_for_meta_desc != None:
                meta_description = paragraph_to_use_for_meta_desc.text

    if meta_description == None:
        meta_description = ""

    # do not index stub descriptions from the IndieWeb wiki

    if meta_description.startswith("This article is a stub.") or (
        homepage_meta_description != ""
        and meta_description == homepage_meta_description
    ):
        stub = [p for p in page_desc_soup.find_all("p") if "stub" in p.text]

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

    if page_desc_soup.find("title") != None:
        doc_title = page_desc_soup.find("title").text
    elif page_desc_soup.find("h1") != None:
        doc_title = page_desc_soup.find("h1").text
    else:
        doc_title = page_url

    if doc_title == "":
        doc_title = page_url

    return (
        page_text,
        page_desc_soup,
        published_on,
        final_meta_description,
        doc_title,
        False,
    )
