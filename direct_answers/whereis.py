import mf2py
import requests

def parse_geo(soup):
    h_geo = soup.select(".h-geo")

    if not h_geo:
        h_geo = soup.select(".p-location")

    if len(h_geo) > 0:
        h_geo = h_geo[0]
        lat = h_geo.select(".p-latitude")[0]["value"]
        long = h_geo.select(".p-longitude")[0]["value"]

        if lat and long:
            r = requests.get("https://atlas.p3k.io/map/img?marker[]=lat:{};lng:{};icon:small-blue-cutout&basemap=gray&width=600&height=240&zoom=14".format(lat, long))

            return "<img src='{}' style='float: right;' />".format("https://atlas.p3k.io/map/img?marker[]=lat:{};lng:{};icon:small-blue-cutout&basemap=gray&width=600&height=240&zoom=14".format(lat, long))

    return None