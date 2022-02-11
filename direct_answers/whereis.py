from bs4 import BeautifulSoup
from typing import Tuple, Dict, Any


def parse_geo(soup: BeautifulSoup) -> Tuple[str, Dict[str, Any]]:
    h_geo = soup.select(".h-geo")

    if not h_geo:
        h_geo = soup.select(".p-location")

    if len(h_geo) == 0:
        return None, None

    h_geo = h_geo[0]
    lat = h_geo.select(".p-latitude")
    long = h_geo.select(".p-longitude")

    if lat and long:
        return "<img src='{}' style='float: right;' />".format(
            "https://atlas.p3k.io/map/img?marker[]=lat:{};lng:{};icon:small-blue-cutout&basemap=gray&width=600&height=240&zoom=14".format(
                lat, long
            )
        )

    return None, None