import datetime
import json
import logging

import indieweb_utils
import mf2py
from bs4 import Comment

import crawler.identify_special_snippet as identify_special_snippet


def get_featured_image(page_content: BeautifulSoup):
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


def remove_scripts_and_comments(page_content):
    # remove script and style tags from page_content

    for script in page_content(["script", "style"]):
        script.decompose()

    # remove HTML comments
    # we don't want to include these in rankings

    comments = page_content.findAll(text=lambda text: isinstance(text, Comment))
    [comment.extract() for comment in comments]

    return page_content


def identify_page_type(h_entry_object):
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

    if page_as_h_entry is not None:
        post_type = indieweb_utils.get_post_type(page_as_h_entry)

    return mf2_property_type, post_type, category


def get_favicon(page_content):
    # get site favicon
    favicon = page_content.find("link", rel="shortcut icon")

    if favicon:
        favicon = favicon.get("href")

    if not favicon:
        favicon = page_content.find("link", rel="icon")

    if not favicon:
        favicon = ""

    return favicon


def add_to_database(
    full_url,
    published_on,
    doc_title,
    meta_description,
    heading_info,
    page,
    pages_indexed,
    page_content,
    outgoing_links,
    crawl_budget,
    nofollow_all,
    main_page_content,
    original_h_card,
    hash,
    thin_content=False,
):

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
    page_content = remove_scripts_and_comments(page_content)
    featured_image = get_featured_image(page_content)
    mf2_property_type, post_type, category = identify_page_type(h_entry_object)

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
        "post_type": "",
    }

    with open("results.json", "a+") as f:
        f.write(json.dumps(record))
        f.write("\n")

    logging.info(f"indexed new page {full_url} ({pages_indexed}/{crawl_budget})")

    pages_indexed += 1

    return pages_indexed
