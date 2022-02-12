import logging
from typing import List

import requests

import config


def find_robots_directives(site_url: str) -> List[list]:
    """
    Finds the robots.txt file on a website, reads the contents, then follows directives.

    :param site_url: The url of the site to find the robots.txt file on.
    :type site_url: str
    :return: A list of the allowed and disallowed paths, all URLs in the sitemap, and the protocol used by the site.
    :rtype: List[list]
    """

    protocol = "https://"

    try:
        r = requests.get(
            "https://" + site_url,
            headers=config.HEADERS,
            timeout=5,
            allow_redirects=True,
            verify=False,
        )
    except Exception as e:
        print(e)
        pass

    try:
        r = requests.get(
            "http://" + site_url,
            headers=config.HEADERS,
            timeout=5,
            allow_redirects=True,
            verify=False,
        )
        protocol = "http://"
    except requests.exceptions.ConnectionError as e:
        print(e)
        print(f"error with {site_url} url and site, skipping")
        return

    # get accept header
    accept = r.headers.get("accept")

    if accept:
        headers = config.HEADERS
        headers["accept"] = accept.split(",")[0]

    # allow five redirects before raising an exception
    session = requests.Session()
    session.max_redirects = 5

    try:
        read_robots = session.get(
            f"{protocol}{site_url}/robots.txt",
            headers=config.HEADERS,
            timeout=5,
            allow_redirects=True,
            verify=False,
        )
    except requests.exceptions.ConnectionError:
        # "Error: Could not find robots.txt file on {}".format(site_url))
        logging.error(f"Error: Could not find robots.txt file on {site_url}")
        return [], [], protocol

    if read_robots.status_code == 404:
        logging.warning(f"Robots.txt not found on {site_url}")
        return [], [f"{protocol}{site_url}/sitemap.xml"], protocol

    namespaces_to_ignore = []

    next_line_is_to_be_read = False

    sitemap_urls = []

    for processed_line in read_robots.content.decode("utf-8").split("\n"):
        # Only read directives pointed at all user agents or my crawler user agent
        if (
            "User-agent: *" in processed_line
            or "User-agent: indieweb-search" in processed_line
        ):
            next_line_is_to_be_read = True

        if "Disallow:" in processed_line and next_line_is_to_be_read:
            if processed_line == "Disallow: /*" or processed_line == "Disallow: *":
                # print("All URLs disallowed. Crawl complete")
                return namespaces_to_ignore, sitemap_urls, protocol
            namespaces_to_ignore.append(processed_line.split(":")[1].strip())
        elif "Sitemap:" in processed_line and next_line_is_to_be_read:
            # Second : will be in the URL of the sitemap so it needs to be preserved
            sitemap_url = (
                processed_line.split(":")[1] + ":" + processed_line.split(":")[2]
            )
            sitemap_urls.append(sitemap_url.strip())
        elif len(processed_line) == 0:
            next_line_is_to_be_read = False

    if sitemap_urls == []:
        sitemap_urls.append(f"https://{site_url}/sitemap.xml")

    return namespaces_to_ignore, sitemap_urls, protocol
