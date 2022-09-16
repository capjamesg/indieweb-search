import csv
import datetime
import logging
from typing import List

from write_logs import write_log


def page_link_discovery(
    links: list,
    final_urls: list,
    crawl_queue: list,
    page_being_processed: str,
    all_links: list,
    external_links: list,
    discovered_urls: list,
    site_url: str,
    crawl_depth: int,
) -> List[list]:
    """
    Find all the links on the page and adds them to the list of links to crawl.
    """

    discovered_urls = {}

    for link in links:

        if link is None:
            continue

        if not link.get("href"):
            continue

        link["href"] = link["href"].lower().strip().replace("http://", "https://")

        supported_protocols = ["http", "https"]

        # remove # from the end of the link
        if "#" in link["href"]:
            link["href"] = link["href"].split("#")[0]

        if link["href"].startswith("/"):
            full_link = f"https://{site_url}" + link["href"]

        if (
            link["href"]
            and not link["href"].startswith("/")
            and (
                "://" in link.get("href")
                and link.get("href").split("://")[0] not in supported_protocols
            )
            or (
                ":" in link.get("href")
                and (
                    not link.get("href").startswith("/")
                    and not link.get("href").startswith("//")
                    and not link.get("href").startswith("#")
                    and not link.get("href").split(":")[0] in supported_protocols
                )
            )
        ):
            # url is wrong protocol, continue

            write_log(
                "Unsupported protocol for discovered url: "
                + link.get("href")
                + ", not adding to index queue",
                domain=site_url,
            )
            continue

        if link.get("href").startswith("#"):
            continue

        link["href"] = link["href"].split("?")[0]

        if link["href"].startswith("//"):
            all_links.append(
                [
                    page_being_processed,
                    link.get("href"),
                    datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "external",
                ]
            )
            external_links["https://" + link["href"]] = page_being_processed
            continue

        # skip email addresses
        if "@" in link["href"]:
            continue

        # Add start of URL to end of any links that don't have it
        if link["href"].startswith("http"):
            full_link = link["href"]
        else:
            if ".." not in link["href"]:
                protocol = page_being_processed.split("://")[0]
                full_link = f"{protocol}://{site_url}/{link['href']}"
            else:
                continue

        if "?" in full_link:
            full_link = full_link[: full_link.index("?")]

        if full_link.endswith("//"):
            full_link = full_link[:-1]

        if "./" in full_link:
            full_link = full_link.replace("./", "")

        # make sure urls with // are processed correctly
        # example: https://www.test.com//text.html should become https://www.test.com/text.html
        if "//" in full_link.replace("://", ""):
            if full_link.startswith("http://"):
                protocol = "http://"
            elif full_link.startswith("https://"):
                protocol = "https://"

            url = (
                full_link.replace("http://", "")
                .replace("https://", "")
                .replace("//", "/")
            )

            full_link = protocol + url

        if (
            full_link not in final_urls.keys()
            and (
                full_link.startswith(f"https://{site_url}")
                or full_link.startswith(f"http://{site_url}")
            )
            and not full_link.startswith("//")
            and len(final_urls) < 30000
        ):
            all_links.append(
                [
                    page_being_processed,
                    link.get("href"),
                    datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "internal",
                    link.text,
                ]
            )

            write_log("indexing queue now contains " + full_link, site_url)
            final_urls[full_link] = ""

            crawl_queue.append(full_link)

            # add 1 to crawl depth
            discovered_urls[full_link] = crawl_depth + 1

    return final_urls, crawl_queue, all_links, external_links, discovered_urls
