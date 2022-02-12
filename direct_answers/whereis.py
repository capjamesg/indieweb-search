from typing import Any, Dict, Tuple

from bs4 import BeautifulSoup

from .structures import DirectAnswer


def parse_geo(soup: BeautifulSoup) -> DirectAnswer:
    """
    Retrieve h-geo microformat data from a post.

    :param soup: The BeautifulSoup object of the post.
    :type soup: BeautifulSoup

    :return: A DirectAnswer object.
    :rtype: DirectAnswer
    """
    h_geo = soup.select(".h-geo")

    if not h_geo:
        h_geo = soup.select(".p-location")

    if len(h_geo) == 0:
        return None, None

    h_geo = h_geo[0]
    lat = h_geo.select(".p-latitude")
    long = h_geo.select(".p-longitude")

    if lat and long:
        html = "<img src='{}' style='float: right;' />".format(
            "https://atlas.p3k.io/map/img?marker[]=lat:{};lng:{};icon:small-blue-cutout&basemap=gray&width=600&height=240&zoom=14".format(
                lat, long
            )
        )

        return DirectAnswer(
            answer_html=html,
            answer_type="direct_answer",
            breadcrumb="IndieWeb Search Direct Answer",
            title=soup.find("title").text,
        )

    return None, None
