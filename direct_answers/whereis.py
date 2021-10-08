import mf2py

def parse_geo(original_cleaned_value, soup, url, original_url):
    h_geo = soup.select(".h-geo")

    if len(h_geo) > 0:
        h_geo = h_geo[0]
        lat = h_geo.get("latitude")
        long = h_geo.get("longitude")
        altitude = h_geo.get("altitude")

        return 

    return None, None