import datetime
from typing import List, Tuple
from wsgiref import headers

import requests
from bs4 import BeautifulSoup

import config
import crawler.url_handling_helpers as url_handling_helpers
import crawler.verify_and_process as verify_and_process
from write_logs import write_log


def remove_repeated_fragments_from_title(doc_title: str, home_page_title: str) -> str:
    """
    Check if the title of a page is a duplicate of another page.

    :param doc_title: the title of the page
    :type doc_title: str
    :param home_page_title: the title of the home page
    :type home_page_title: str

    :return: the title of the page if it is a duplicate, the original title if not
    :rtype: str
    """

    separators = [" | ", " - ", " • "]

    for sep in separators:
        if sep in doc_title and sep in home_page_title:
            home_page_title_components = home_page_title.split(sep)[1:]

            for component in home_page_title_components:
                doc_title = doc_title.split(sep)[0]

            # replace separator
            doc_title = doc_title.replace(sep, " ")

            doc_title = doc_title.strip()

            break

    return doc_title


def parse_link_headers(
    page_test: requests.Response,
    full_url: str,
    crawl_queue: list,
    discovered_urls: dict,
) -> bool:
    """
    Check if page is canonical according to its link headers.

    :param page_test: the response object from the request
    :type page_test: requests.Response
    :param full_url: the full url of the page
    :type full_url: str
    :param crawl_queue: the crawl queue
    :type crawl_queue: list
    :param discovered_urls: the discovered urls
    :type discovered_urls: dict

    :return: True if the page is canonical, False if not
    :rtype: bool
    """
    if not page_test.headers.get("link"):
        return False

    header_links = requests.utils.parse_header_links(
        page_test.headers.get("link").rstrip(">").replace(">,<", ",<")
    )

    for link in header_links:
        if link["rel"] != "canonical":
            continue

        if link["rel"].startswith("/"):
            continue

        # get site domain
        domain = full_url.split("/")[2]
        link["rel"] = full_url.split("/")[0] + "//" + domain + link["rel"]

        canonical = verify_and_process.find_base_url_path(link["rel"])

        result = url_handling_helpers.parse_canonical(
            canonical,
            full_url,
            link["url"],
            crawl_queue,
            discovered_urls,
        )

        if result:
            return True

    return False


def check_for_redirect_url(
    page_test: requests.Response, full_url: str, site_url: str
) -> str:
    """
    Check if the page is a redirect.

    :param page_test: the response object from the request
    :type page_test: requests.Response
    :param full_url: the full url of the page
    :type full_url: str
    :param site_url: the site url
    :type site_url: str

    :return: the redirect url if the page is a redirect, the full url if not
    :rtype: str
    """
    if (
        page_test.history
        and page_test.history[-1].url
        and page_test.history[-1].url != full_url
    ):
        # skip redirects to external sites
        if not page_test.history[-1].url.startswith(
            "http://" + site_url
        ) and not page_test.history[-1].url.startswith("https://" + site_url):
            write_log(
                "{} redirected to {}, which is on a different site, skipping".format(
                    full_url, page_test.history[-1].url
                ),
                site_url,
            )
            write_log(
                "{} redirected to {}, which is on a different site, skipping".format(
                    full_url, page_test.history[-1].url
                ),
                site_url,
            )
            raise Exception

        write_log(f"{full_url} redirected to {page_test.history[-1].url}", site_url)

        full_url = page_test.history[-1].url

    return full_url


def initial_url_checks(full_url: str) -> None:
    """
    Check if a URL is eligible to be crawled.

    :param full_url: the full url of the page
    :type full_url: str

    :return: None
    :rtype: None
    """
    if len(full_url) > 125:
        write_log(f"{full_url} url too long, skipping")
        raise Exception

    if "javascript:" in full_url:
        write_log(f"{full_url} marked as noindex because it is a javascript resource")
        raise Exception

    if "/wp-json/" in full_url:
        write_log(
            f"{full_url} marked as noindex because it is a wordpress api resource"
        )
        raise Exception

    if "?s=" in full_url:
        write_log(f"{full_url} marked as noindex because it is a search result")
        raise Exception

    # there are a few wikis in the crawl and special pages provide very little value to the search index
    if "/Special:" in full_url:
        write_log(f"{full_url} is a MediaWiki special page, will not crawl")
        raise Exception

    if "/page/" in full_url and full_url.split("/")[-1].isdigit():
        write_log(f"{full_url} marked as follow, noindex because it is a page archive")
        url_handling_helpers.check_remove_url(full_url)
        raise Exception

    if (
        "/tags/" in full_url
        or "/tag/" in full_url
        or "/label/" in full_url
        or "/search/" in full_url
        or "/category/" in full_url
        or "/categories/" in full_url
    ):
        write_log(
            "{} marked as follow, noindex because it is a tag, label, or search resource".format(
                full_url
            )
        )
        raise Exception


def check_if_url_is_noindexed(
    page_html_contents: BeautifulSoup, full_url: str
) -> List[bool]:
    """
    Check if a URL has been marked as noindex.

    :param page_html_contents: the page contents
    :type page_html_contents: BeautifulSoup
    :param full_url: the full url of the page
    :type full_url: str

    :return: a list of booleans, the first is if the page is noindexed, the second is if the page is nofollow
    :rtype: List[bool]
    """
    nofollow_all = False

    check_if_no_index = page_html_contents.find("meta", {"name": "robots"})

    if (
        check_if_no_index
        and check_if_no_index.get("content")
        and (
            "noindex" in check_if_no_index.get("content")
            or "none" in check_if_no_index.get("content")
        )
    ):
        write_log(f"{full_url} marked as noindex, skipping")
        url_handling_helpers.check_remove_url(full_url)
        raise Exception

    elif (
        check_if_no_index
        and check_if_no_index.get("content")
        and "nofollow" in check_if_no_index.get("content")
    ):
        write_log(
            "all links on {} marked as nofollow due to <meta> robots nofollow value".format(
                full_url
            )
        )
        nofollow_all = True

    return check_if_no_index, nofollow_all


def get_main_page_text(page_html_contents: str) -> BeautifulSoup:
    """
    Get the main body of a page from its BeautifulSoup object.

    :param page_html_contents: the page contents
    :type page_html_contents: BeautifulSoup

    :return: the main body of the page
    :rtype: BeautifulSoup
    """

    selectors_to_check = (".e-content", ".h-entry")

    for s in selectors_to_check:
        if page_html_contents.select(s):
            page_text = page_html_contents.select(s)[0]

    tags_to_find = (
        ("main", {}),
        ("div", {"id": "main"}),
        ("div", {"id": "app"}),
        ("div", {"id": "page"}),
        ("div", {"id": "site-container"}),
        ("div", {"id": "application-main"}),
        ("body", {}),
        ("html", {}),
    )

    for tag in tags_to_find:
        tag_name = tag[0]
        tag_selector = tag[1]

        if page_html_contents.find(tag) and tag_selector != {}:
            page_text = page_html_contents.find(tag_name, tag_selector)
        elif page_html_contents.find(tag):
            page_text = page_html_contents.find(tag)

    return page_text


def initial_head_request(
    full_url: str,
    session: requests.Session,
    site_url: str,
    etag: str,
    date_crawled: str,
) -> list:
    """
    Make initial head request to a url.
    """
    nofollow_all = False

    conditional_headers = {
        "If-None-Match": etag,
        "If-Modified-Since": date_crawled,
    }

    try:
        # Check if page is the right content type before indexing
        page_test = session.head(
            full_url,
            headers=config.HEADERS + conditional_headers,
            allow_redirects=True,
            verify=False,
        )
    except requests.exceptions.Timeout:
        write_log(f"{full_url} timed out, skipping", site_url)
        url_handling_helpers.check_remove_url(full_url)
        raise Exception
    except requests.exceptions.TooManyRedirects:
        write_log(f"{full_url} too many redirects, skipping", site_url)
        url_handling_helpers.check_remove_url(full_url)
        raise Exception
    except:
        write_log(f"{full_url} failed to connect, skipping", site_url)
        raise Exception

    # get redirect count
    redirect_history = page_test.history
    redirect_count = len(redirect_history)

    # get redirect url
    full_url = check_for_redirect_url(page_test, full_url, site_url)

    if page_test.headers.get("x-robots-tag"):
        # only obey directives pointed at indieweb-search or everyone
        if "indieweb-search:" in page_test.headers.get(
            "x-robots-tag"
        ) or ":" not in page_test.headers.get("x-robots-tag"):
            if "noindex" in page_test.headers.get(
                "x-robots-tag"
            ) or "none" in page_test.headers.get("x-robots-tag"):
                write_log(f"{full_url} marked as noindex", site_url)
                raise Exception
            elif "nofollow" in page_test.headers.get("x-robots-tag"):
                write_log(
                    "all links on {} marked as nofollow due to x-robots-tag nofollow value".format(
                        full_url
                    ),
                    site_url,
                )
                nofollow_all = True

    content_type_is_valid = verify_content_type_is_valid(page_test, full_url)

    if content_type_is_valid is False:
        raise Exception

    if page_test.status_code == 304:
        headers = {"Authorization": config.ELASTICSEARCH_API_TOKEN}

        requests.post(
            "https://es-indieweb-search.jamesg.blog/add_to_queue",
            headers=headers,
            data={"url": full_url},
        )

        # raise exception here so URL doesn't continue to be crawled
        raise Exception

    return page_test, nofollow_all, redirect_count


def filter_adult_content(page_html_contents: BeautifulSoup, full_url: str) -> bool:
    """
    Check if a page is marked as adult content per the rating meta tag.
    """
    if page_html_contents.find("meta", {"name": "rating"}):
        if (
            page_html_contents.find("meta", {"name": "rating"}).get("content")
            == "adult"
            or page_html_contents.find("meta", {"name": "rating"}).get("content")
            == "RTA-5042-1996-1400-1577-RTA"
        ):
            write_log(
                f"{full_url} marked as adult content in a meta tag, skipping",
                full_url.split("/")[2],
            )
            raise Exception


def verify_content_type_is_valid(page_test: requests.Response, full_url: str) -> bool:
    """
    Verify the content on a page is HTML.
    """
    if (
        page_test.headers
        and page_test.headers.get("content-type")
        and "text/html" not in page_test.headers["content-type"]
    ):
        url_handling_helpers.check_remove_url(full_url)
        return False

    return True


def check_meta_equiv_refresh(
    url: str,
    feeds: list,
    hash: str,
    crawl_depth: int,
    average_crawl_speed: list,
    page_html_contents: BeautifulSoup,
    discovered_urls: dict,
    full_url: str,
) -> Tuple[str, list, bool, list, str, int, list]:
    """
    Check if a page has a meta equiv refresh tag.
    """
    if page_html_contents.find("meta", attrs={"http-equiv": "refresh"}):
        refresh_url = (
            page_html_contents.find("meta", attrs={"http-equiv": "refresh"})["content"]
            .split(";")[1]
            .split("=")[1]
        )

        refresh_domain = refresh_url.split("/")[2]

        if refresh_domain.lower().replace("www.", "") != full_url.split("/")[
            2
        ].lower().replace("www.", ""):
            write_log(
                "{} has a refresh url of {}, not adding to queue because url points to a different domain".format(
                    full_url, refresh_url
                ),
                full_url.split("/")[2],
            )

            return url, {}, False, feeds, hash, crawl_depth, average_crawl_speed

        if refresh_url:
            discovered_urls[refresh_url] = refresh_url

        # add new page to crawl queue so that previous validation can happen again (i.e. checking for canonical header)
        return (
            url,
            discovered_urls,
            False,
            feeds,
            hash,
            crawl_depth,
            average_crawl_speed,
        )


def handle_redirect(
    page: requests.Session,
    final_urls: list,
    crawl_queue: list,
    url: str,
    feeds: list,
    crawl_depth: int,
    average_crawl_speed: list,
    discovered_urls: dict,
    full_url: list,
) -> Tuple[str, list, bool, list, str, int, list]:
    """
    Handle a redirect response from a page.
    """
    redirected_to = page.headers["Location"]

    if not redirected_to:
        final_urls[redirected_to] = ""

        crawl_queue.append(redirected_to)

        # don't index a url if it was redirected from a canonical and wants to redirect again
        if discovered_urls.get(full_url) and discovered_urls.get(full_url).startswith(
            "CANONICAL"
        ):
            split_value = discovered_urls.get(full_url).split(" ")
            redirected_from = split_value[1]
            if redirected_from == redirected_to:
                write_log(
                    "{} has already been redirected from a canonical url, will not redirect a second time, skipping".format(
                        full_url
                    ),
                    full_url.split("/")[2],
                )
                return (
                    url,
                    discovered_urls,
                    False,
                    feeds,
                    None,
                    crawl_depth,
                    average_crawl_speed,
                )

        discovered_urls[redirected_to] = redirected_to

    return (
        url,
        discovered_urls,
        False,
        feeds,
        None,
        crawl_depth,
        average_crawl_speed,
    )


def get_web_page(session: requests.Session, full_url: str) -> requests.Response:
    """
    Retrieve a web page using a HTTP GET request.

    :param session: A requests session object.
    :type session: requests.Session
    :param full_url: The full url of the page to retrieve.
    :type full_url: str

    :return: A requests response object.
    :rtype: requests.Response
    """
    try:
        page = session.get(
            full_url,
            timeout=10,
            headers=config.HEADERS,
            allow_redirects=True,
            verify=False,
        )
    except requests.exceptions.Timeout:
        write_log(f"{full_url} timed out, skipping", full_url.split("/")[2])
        raise Exception
    except requests.exceptions.TooManyRedirects:
        write_log(f"{full_url} too many redirects, skipping", full_url.split("/")[2])
        url_handling_helpers.check_remove_url(full_url)
        raise Exception
    except:
        write_log(f"{full_url} failed to connect, skipping", full_url.split("/")[2])
        raise Exception

    # 404 = not found, 410 = gone
    if page.status_code == 404 or page.status_code == 410:
        raise Exception

    elif page.status_code != 200:
        url_handling_helpers.check_remove_url(full_url)
        write_log(
            f"{full_url} page {page.status_code} status code", full_url.split("/")[2]
        )
        raise Exception

    content_type_is_valid = verify_content_type_is_valid(page, full_url)

    if content_type_is_valid is False:
        raise Exception

    return page


def link_discovery_processing(
    page: requests.Response, site: str, full_url: str, feeds: list, feed_urls: list
) -> Tuple[list]:
    """
    Process the headers in a link and look for websub hubs and feeds.

    :param page: A requests response object.
    :type page: requests.Response
    :param site: The site URL.
    :type site: str
    :param full_url: The full url of the page being processed.
    :type full_url: str
    :param feeds: A list of feeds found on the page.
    :type feeds: list
    :param feed_urls: A list of feed urls found on the page.
    :type feed_urls: list

    :return: A list of feeds found on the page and a list of feed urls found on the page.
    :rtype: Tuple[list]
    """
    # check for feed with rel alternate
    # only support rss and atom right now

    # feeds, feed_urls = url_handling_helpers.find_feeds(page_html_contents, full_url, site)

    # parse link headers
    link_headers = page.headers.get("Link")

    if not link_headers:
        return feeds, feed_urls

    link_headers = link_headers.split(",")

    for link_header in link_headers:
        if 'rel="hub"' in link_header and len(feeds) < 25:
            websub_hub = link_header.split(";")[0].strip().strip("<").strip(">")

            feeds.append(
                {
                    "website_url": site,
                    "page_url": full_url,
                    "feed_url": websub_hub,
                    "mime_type": "websub",
                    "etag": "NOETAG",
                    "discovered": datetime.datetime.now().strftime("%Y-%m-%d"),
                }
            )

            feed_urls.append(full_url.strip("/"))

            write_log(f"{websub_hub} is a websub hub, will save to feeds.json")

        if 'rel="alternate"' in link_header and len(feeds) < 25:
            original_feed_url = (
                link_header.split(";")[0].strip().strip("<").strip(">").lower()
            )

            if original_feed_url in feed_urls:
                continue

            # get feed type
            if 'type="' in link_header:
                feed_type = link_header.split('type="')[1].split('"')[0]
            else:
                feed_type = "feed"

            if original_feed_url.startswith("/"):
                # get site domain
                domain = full_url.split("/")[2]
                feed_url = full_url.split("/")[0] + "//" + domain + original_feed_url

                if feed_url and feed_url not in feed_urls:
                    feeds, feed_urls = url_handling_helpers.save_feed(
                        site,
                        full_url,
                        original_feed_url,
                        feed_type,
                        feeds,
                        feed_urls,
                    )
            elif original_feed_url.startswith("http"):
                if (
                    original_feed_url not in feed_urls
                    and original_feed_url.split("/")[2] == full_url.split("/")[2]
                ):
                    feeds, feed_urls = url_handling_helpers.save_feed(
                        site,
                        full_url,
                        original_feed_url,
                        feed_type,
                        feeds,
                        feed_urls,
                    )
            else:
                feeds, feed_urls = url_handling_helpers.save_feed(
                    site,
                    full_url,
                    original_feed_url,
                    feed_type,
                    feeds,
                    feed_urls,
                )

    return feeds, feed_urls
