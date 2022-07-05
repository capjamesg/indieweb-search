import datetime
import json

import indieweb_utils
import mf2py
import requests
from bs4 import BeautifulSoup, Comment

import crawler.identify_special_snippet as identify_special_snippet
from write_logs import write_log


def get_featured_image(page_content: BeautifulSoup) -> str:
    """
    Retrieve the featured image for a page (if one is available).
    """
    # get featured image if one is available
    # may be presented in featured snippets
    featured_image = None

    if page_content.find(".u-featured"):
        featured_image = page_content.find(".u-featured").get("src")

    elif page_content.find(".u-photo"):
        featured_image = page_content.find(".u-photo").get("src")

    elif page_content.find("meta", property="og:image"):
        featured_image = page_content.find("meta", property="og:image").get("src")

    elif page_content.find("meta", property="twitter:image"):
        featured_image = page_content.find("meta", property="twitter:image").get("src")

    else:
        featured_image = ""

    return featured_image


def get_json_ld(page_content: BeautifulSoup) -> dict:
    """
    Get the JSON-LD for a page.
    """
    # get JSON-LD
    json_lds = page_content.find_all("script", type="application/ld+json")

    for item in json_lds:
        print(item)
        if "Product" in item.text:
            print(item.text)
            return json.loads(item.text)

    json_ld = {}

    return json_ld


def remove_scripts_and_comments(page_content: BeautifulSoup) -> BeautifulSoup:
    """
    Remove script and comment tags from the page content.
    """
    # remove script and style tags from page_content

    for script in page_content(["script", "style"]):
        script.decompose()

    # remove HTML comments
    # we don't want to include these in rankings

    comments = page_content.findAll(text=lambda text: isinstance(text, Comment))
    [comment.extract() for comment in comments]

    return page_content


def identify_page_type(h_entry_object: dict) -> list:
    """
    Retrieve the name of an mf2 property on a page and the main post type for the page.
    """
    page_as_h_entry = ""
    mf2_property_type = None
    post_type = ""
    category = ""

    for item in h_entry_object["items"]:
        if item["type"] and item["type"] == ["h-entry"]:
            page_as_h_entry = item

            if item.get("category"):
                category = ", ".join(item["category"])

            if item.get("like-of"):
                mf2_property_type = "like-of"
            elif item.get("repost-of"):
                mf2_property_type = "repost-of"
            elif item.get("bookmark-of"):
                mf2_property_type = "bookmark-of"

            break

    if page_as_h_entry is not None and type(page_as_h_entry) == dict:
        try:
            post_type = indieweb_utils.get_post_type(page_as_h_entry)
        except:
            post_type = ""

    return mf2_property_type, post_type, category


def get_favicon(page_content: BeautifulSoup) -> str:
    """
    Get the favicon for a page.
    """
    # get site favicon
    favicon = page_content.find("link", rel="shortcut icon")

    if favicon:
        favicon = favicon.get("href")

    if not favicon:
        favicon = page_content.find("link", rel="icon")

        if favicon:
            favicon = favicon.get("href")

    if not favicon:
        favicon = ""

    return favicon


def save_to_file(
    full_url: str,
    published_on: str,
    doc_title: str,
    meta_description: str,
    heading_info: dict,
    page: requests.Response,
    pages_indexed: int,
    page_content: str,
    outgoing_links: int,
    crawl_budget: int,
    nofollow_all: bool,
    main_page_content: BeautifulSoup,
    original_h_card: dict,
    hash: str,
    thin_content: bool = False,
) -> int:
    """
    Finish processing a page and save it to a results.json file.
    """

    # the program will try to populate all of these values before indexing a document
    category = None
    special_snippet = {}
    h_card = None
    favicon = ""
    length = len(page_content)
    is_homepage = False

    if page != "" and page.headers:
        length = page.headers.get("content-length", "")

    h_entry_object = mf2py.parse(page_content)

    special_snippet, h_card = identify_special_snippet.find_snippet(
        page_content, h_card
    )

    if h_card == []:
        h_card = indieweb_utils.discover_author(
            h_card, h_entry_object, full_url, original_h_card
        )

    favicon = get_favicon(page_content)
    featured_image = get_featured_image(page_content)
    mf2_property_type, post_type, category = identify_page_type(h_entry_object)
    json_ld = get_json_ld(page_content)
    page_content = remove_scripts_and_comments(page_content)

    # find out if page is home page
    if (
        full_url.replace("https://", "").replace("http://", "").strip("/").count("/")
        == 0
    ):
        is_homepage = True

    record = {
        "title": doc_title,
        "meta_description": meta_description,
        "url": full_url,
        "published_on": published_on,
        "h1": ", ".join(heading_info["h1"]),
        "h2": ", ".join(heading_info["h2"]),
        "h3": ", ".join(heading_info["h3"]),
        "h4": ", ".join(heading_info["h4"]),
        "h5": ", ".join(heading_info["h5"]),
        "h6": ", ".join(heading_info["h6"]),
        "length": length,
        "page_content": str(page_content),
        "incoming_links": 0,
        "page_text": page_content.get_text(),
        "outgoing_links": outgoing_links,
        "domain": full_url.split("/")[2],
        "word_count": len(main_page_content.get_text().split(" ")),
        "last_crawled": datetime.datetime.today().strftime("%Y-%m-%d %H:%M:%S"),
        "favicon": favicon,
        "referring_domains_to_site": 0,  # updated when index is rebuilt
        "internal_incoming_links": 0,  # not actively used
        "http_headers": str(page.headers),
        "page_is_nofollow": nofollow_all,
        "h_card": json.dumps(h_card),
        "is_homepage": is_homepage,
        "category": category,
        "featured_image": featured_image,
        "thin_content": thin_content,
        "page_hash": hash,
        "special_snippet": special_snippet,
        "mf2_property_type": mf2_property_type,
        "post_type": post_type,
        "json_ld": json.dumps(json_ld),
    }

    with open("results.json", "a+") as f:
        f.write(json.dumps(record))
        f.write("\n")

    write_log(
        f"crawled new page {full_url} ({pages_indexed}/{crawl_budget})",
        full_url.split("/")[2],
    )

    pages_indexed += 1

    return pages_indexed
