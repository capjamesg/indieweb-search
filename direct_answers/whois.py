import os

import indieweb_utils
import mf2py
from bs4 import BeautifulSoup

from .structures import DirectAnswer


def parse_whois(
    original_cleaned_value: str, soup: BeautifulSoup, url: str, original_url: str
) -> DirectAnswer:
    """
    Parse and return h-card information from a post (if available).

    :param original_cleaned_value: The cleaned value of the search term.
    :param soup: The BeautifulSoup object of the post.
    :param url: The URL of the post.

    :return: A DirectAnswer object.
    :rtype: DirectAnswer
    """
    if "who is" in original_cleaned_value or (
        (
            "." in original_cleaned_value
            and len(original_cleaned_value.split(".")[0]) > 3
            and len(original_cleaned_value.split(".")[0]) > 1
            and len(original_cleaned_value.split(" ")) == 1
        )
    ):
        mf2s = mf2py.parse(doc=soup)["items"]

        h_card = ""

        for item in mf2s:
            if item.get("type") and item.get("type")[0] == "h-card":
                h_card = item
                break

        if h_card == "":
            for item in mf2s:
                if (
                    item.get("type")
                    and item.get("type")[0] == "h-entry"
                    and item.get("properties")
                    and item.get("properties").get("author")
                ):
                    h_card = item.get("properties").get("author")[0]
                    break

        if h_card is None:
            return None

        to_show = ""

        if len(h_card) == 0:
            return None

        name = h_card["properties"].get("name")

        if name:
            name = h_card["properties"].get("name")[0]
        else:
            name = ""

        photo_url = h_card["properties"].get("photo")

        if photo_url:
            photo = indieweb_utils.canonicalize_url(
                h_card["properties"].get("photo"), url
            )
        else:
            photo = ""

        for key, value in h_card["properties"].items():
            if (
                key != "photo"
                and key != "email"
                and key != "logo"
                and key != "url"
                and key != "uid"
                and type(value[0]) == str
            ):
                if value[0].startswith("/"):
                    value[0] = url.strip("/") + "/" + value[0]
                elif value[0].startswith("http"):
                    value[0] = value[0]
                elif value[0].startswith("//"):
                    value[0] = url.strip("/") + "/" + value[0]
                elif value[0].startswith("./"):
                    value[0] = "<a href='{}'>{}</a>".format(
                        url.strip("./") + "/" + value[0],
                        url.strip("./") + "/" + value[0],
                    )

                to_show += "<p><b>{}</b>: {}</p>".format(
                    key.title().replace("-", " "), value[0]
                )
            elif key == "email" and "@" in value[0]:
                # @ must be in email for it to be valid
                to_show += "<p><b>{}</b>: <a href='{}'>{}</a></p>".format(
                    key.title(),
                    "mailto:{}".format(value[0].replace("mailto:", "")),
                    value[0].replace("mailto:", ""),
                )
            elif key == "url":
                if value[0].strip() == "":
                    to_show += "<p><b>{}</b>: <a href='{}'>{}</a></p>".format(
                        "URL", original_url, original_url
                    )
                else:
                    if not value[0].startswith("http"):
                        value[0] = url.strip("/") + "/" + value[0].strip("/")

                    to_show += "<p><b>{}</b>: <a href='{}'>{}</a></p>".format(
                        "URL", value[0], value[0].strip("/")
                    )

        if soup.find("h1"):
            title = soup.find("h1").text
        else:
            title = url

        html = "<img src='{}' height='100' width='100' style='float: right;'><p>{}</p>".format(
            photo, to_show
        )

        return DirectAnswer(
            answer_html=html,
            answer_type="direct_answer",
            breadcrumb=original_url,
            title=title,
        )

    return None, None


def parse_social(
    original_cleaned_value: str, soup: BeautifulSoup, url: str, original_url: str
) -> DirectAnswer:
    """
    Parse and return rel=me information from a web page.

    :param original_cleaned_value: The cleaned value of the search term.
    :param soup: The BeautifulSoup object of the post.
    :param url: The URL of the post.
    :param original_url: The original URL of the post.

    :return: A DirectAnswer object.
    :rtype: DirectAnswer
    """
    if original_cleaned_value.endswith("social"):
        # get all rel=me links
        rel_me_links = soup.find_all("a", {"rel": "me"})

        if len(rel_me_links) == 0:
            return None, None

        to_show = ""

        for link in rel_me_links:
            if not link.get("href"):
                continue

            link_type = link.text.strip()

            # find file in static/icons
            if (
                link_type
                and link_type != ""
                and os.path.isfile(
                    "static/icons/" + link_type.lower() + "-16x16" + ".png"
                )
            ):
                image = (
                    "<img src='/static/icons/"
                    + link_type.lower()
                    + "-16x16"
                    + ".png' height='15' width='15' style='display: inline;'>"
                )
                to_show += "<li>{}<a href='{}'> {}</a></li>".format(
                    image, link.get("href"), link_type
                )
            elif link_type and link_type != "":
                to_show += "<li><a href='{}'>{}</a></li>".format(
                    link.get("href"), link_type
                )
            else:
                to_show += "<li><a href='{}'>{}</a></li>".format(
                    link.get("href"), link.get("href")
                )

        if soup.find("h1"):
            title = soup.find("h1").text
        else:
            title = url

        if to_show == "":
            to_show = "No social links were found on this site's home page."

        html = """<h3>{} Social Links</h3><ul>{}</ul><details><br><summary>How to show up here</summary>
            You can have social links show up by entering 'yourdomainname.com social' into the search engine as long as you have rel=me links set up on your home page.
            Learn how to do this on the <a href='https://indieweb.org/rel-me'>IndieWeb wiki</a>.</details>""".format(
            title, to_show
        )

        return DirectAnswer(
            answer_html=html,
            answer_type="direct_answer",
            breadcrumb=original_url,
            title=title,
        )

    return None, None


def parse_get_rel(
    original_cleaned_value: str, soup: BeautifulSoup, original_url: str
) -> DirectAnswer:
    """
    Get information about all rel= links on a page.

    :param original_cleaned_value: The cleaned value of the search term.
    :param soup: The BeautifulSoup object of the post.
    :param original_url: The original URL of the post.

    :return: A DirectAnswer object.
    :rtype: DirectAnswer
    """

    # get all feeds on a page
    if not original_cleaned_value.endswith("get rel"):
        return None, None

    # get all rel values
    rel_values = soup.select("link[rel]")

    to_show = ""

    for link in rel_values:
        to_show += "<li>{}: <a href='{}'>{}</a></li>".format(
            "".join(link.get("rel")), link.get("href"), link.get("href")
        )

    if to_show == "":
        to_show = "No rel links were found on this site's home page."

    html = "<h3>'Rel' Attributes for {}</h3><ul>{}</ul>".format(
        original_url.replace("https://", "").replace("http://", "").strip("/"),
        to_show,
    )

    return DirectAnswer(
        answer_html=html,
        answer_type="direct_answer",
        breadcrumb=original_url,
        title=soup.find_all("h1")[0].text,
    )


def parse_feed(
    original_cleaned_value: str, soup: BeautifulSoup, url: str
) -> DirectAnswer:
    """
    Retrieve a list of all feeds on a page.

    :param original_cleaned_value: The cleaned value of the search term.
    :param soup: The BeautifulSoup object of the post.
    :param url: The URL of the post.

    :return: A DirectAnswer object.
    :rtype: DirectAnswer
    """
    # get all feeds on a page
    if not original_cleaned_value.endswith("inspect feed"):
        return None, None
    to_show = ""
    feeds = soup.find_all("link", {"rel": "alternate"})

    # check for h-feed
    h_feed = soup.select(".h-feed")

    if h_feed:
        to_show += f"<li><b>Microformats h-feed</b>: <a href='{url}'>{url}</li>"

    if len(feeds) == 0:
        return None, None

    to_show = ""

    for link in feeds:
        if link.get("href"):
            link_type = link.get("type")
            if link_type:
                link_type = link_type.split("/")[1].split("+")

                if link_type is not None:
                    link_type = link_type[0]

                    to_show += "<li><b>{} feed</b>: <a href='{}'>{}</a></li>".format(
                        link_type, link.get("href"), link.get("href")
                    )
                elif link_type == "application/json":
                    link_type = "JSON"

                    to_show += "<li><b>{} feed</b>: <a href='{}'>{}</a></li>".format(
                        link_type, link.get("href"), link.get("href")
                    )
            else:
                to_show += "<li><b>Feed</b>: <a href='{}'>{}</a></li>".format(
                    link.get("href"), link.get("href"), link.get("href")
                )

    if soup.find("h1"):
        title = soup.find("h1").text
    else:
        title = url

    if to_show == "":
        to_show = "No feeds were found on this site's home page."

    html = f"<h3>{title} Feeds</h3><ul>{to_show}</ul>"

    return DirectAnswer(
        answer_html=html,
        answer_type="direct_answer",
        breadcrumb=url,
        title=title,
    )


def parse_address(
    original_cleaned_value: str, soup: BeautifulSoup, url: str
) -> DirectAnswer:
    """
    Parse a h-adr address microformats object and return a result that can be displayed in the search engine.

    :param original_cleaned_value: The cleaned value of the search term.
    :param soup: The BeautifulSoup object of the post.
    :param url: The URL of the post.

    :return: A DirectAnswer object.
    :rtype: DirectAnswer
    """
    # get all addresses on a page
    if not original_cleaned_value.endswith("address"):
        return None, None

    to_show = ""
    addresses = soup.select(".h-adr")

    if len(addresses) == 0:
        return None, None

    address = addresses[0]

    to_show = ""

    supported_properties = [
        "p-street-address",
        "p-extended-address",
        "p-post-office-box",
        "p-locality",
        "p-region",
        "p-postal-code",
        "p-country-name",
    ]

    for i in supported_properties:
        if address.find(i):
            to_show += f"<li><b>{i}</b>: {address.find(i).text}</li>"

    if soup.find("h1"):
        title = soup.find("h1").text
    else:
        title = url

    if to_show == "":
        to_show = "No addresses were found on this site's home page."

    html = f"<h3>{title} Addresses</h3><ul>{to_show}</ul>"

    return DirectAnswer(
        answer_html=html,
        answer_type="direct_answer",
        breadcrumb=url,
        title=title,
    )
