import datetime
import hashlib
from urllib.parse import urlparse as parse_url

import indieweb_utils
import requests
from bs4 import BeautifulSoup

import crawler.calculate_links as calculate_links
import crawler.discovery as page_link_discovery
import crawler.page_info
import crawler.save_record as save_record
import crawler.url_handling_helpers as url_handling_helpers
import crawler.verify_and_process_helpers as verify_and_process_helpers
from crawler.constants import LIKELY_404_TITLES
from write_logs import write_log

yesterday = datetime.datetime.today() - datetime.timedelta(days=1)


def find_base_url_path(url: str) -> str:
    """
    Finds the base path of a URL.

    :param url: The URL whose base path is to be found
    :type url: str

    :return: The base path of the URL
    :rtype: str
    """
    url = url.strip("/").replace("http://", "https://").split("?")[0].lower()

    return url


def filter_nofollow_links(
    page_html_contents: BeautifulSoup, nofollow_all: bool
) -> list:
    """
    Filter out nofollow links on a page.

    :param page_html_contents: The BeautifulSoup object of the page description
    :type page_html_contents: BeautifulSoup
    :param nofollow_all: Whether the page has been classified as "nofollow all links"
    :type nofollow_all: bool

    :return: The list of links on the page
    :rtype: list
    """
    if nofollow_all is False:
        links = [
            l
            for l in page_html_contents.find_all("a")
            if (l.get("rel") and "nofollow" not in l["rel"])
            or (not l.get("rel") and l.get("href") not in ["#", "javascript:void(0);"])
        ]
    else:
        links = []

    return links


def check_if_content_is_thin(word_count: int, number_of_links: int) -> bool:
    """
    Determine whether the content on a page should be classified as "thin".

    :param word_count: The number of words in the page
    :type word_count: int
    :param number_of_links: The number of links on the page
    :type number_of_links: int

    :return: Whether the content on the page should be classified as "thin"
    :rtype: bool
    """
    thin_content = False

    # if the ratio of words to links < 3:1, do not index
    # these pages may be spam or other non-content pages that will not be useful to those using the search engine
    # also filter out pages with 400 words or less
    if (
        (
            word_count
            and (word_count > 0 and number_of_links and number_of_links > 0)
            and word_count > 200
            and word_count / number_of_links < 3
        )
        or (word_count < 400)
        or (number_of_links > 200 and word_count < 3000)
    ):
        thin_content = True

    return thin_content


def detect_soft_404(page_html_contents: BeautifulSoup) -> bool:
    """
    Detects if a page is a soft 404.

    :return: Whether the page is a soft 404
    :rtype: bool
    """

    # get page title
    title = page_html_contents.find("title")

    if title and title == "404":
        return True
    elif title and any(title.text.lower() in s for s in LIKELY_404_TITLES):
        return True

    return False


def crawl_urls(
    final_urls: list,
    pages_indexed: int,
    all_links: list,
    external_links: list,
    discovered_urls: dict,
    crawl_queue: list,
    site_url: str,
    crawl_budget: int,
    url: str,
    feeds: list,
    feed_urls: list,
    site: str,
    session: requests.Session,
    web_page_hashes: list,
    average_crawl_speed: list,
    homepage_meta_description: str,
    link_discovery: bool = True,
    h_card: list = [],
    crawl_depth: int = 0,
    home_page_title: str = "",
    elasticsearch_client: object = None,
    robots_parser: object = None,
) -> tuple:
    """
    Crawls URLs in list, adds URLs to index, and returns updated list.
    """

    budget_used = 0

    feeds = []

    # make sure urls with // are processed correctly
    # example: https://www.test.com//text.html should become https://www.test.com/text.html
    parsed_url = parse_url(url)
    url_domain = parsed_url.netloc
    url_path = parsed_url.path

    full_url = "https://" + url_domain + url_path

    # Do not index URLs blocked in the robots.txt file
    # if (
    #     robots_parser.can_fetch("*", full_url) is False
    # ):
    #     url_handling_helpers.check_remove_url(full_url)
    #     return (
    #         url,
    #         discovered_urls,
    #         False,
    #         feeds,
    #         "",
    #         crawl_depth,
    #         average_crawl_speed,
    #         budget_used,
    #     )

    session.max_redirects = 5

    budget_used += 1

    try:
        (
            page_test,
            nofollow_all,
            redirect_count,
        ) = verify_and_process_helpers.initial_head_request(full_url, session, site_url)
        budget_used += redirect_count
    except:
        print("Error: Could not get page info for: " + full_url)
        url_handling_helpers.check_remove_url(full_url)
        return (
            url,
            discovered_urls,
            False,
            feeds,
            "",
            crawl_depth,
            average_crawl_speed,
            budget_used,
        )

    # has_canonical = verify_and_process_helpers.parse_link_headers(
    #     page_test, full_url, crawl_queue, discovered_urls
    # )

    # if has_canonical == True:
    #     return (
    #         url,
    #         discovered_urls,
    #         False,
    #         feeds,
    #         "",
    #         crawl_depth,
    #         average_crawl_speed,
    #         budget_used,
    #     )

    try:
        page = verify_and_process_helpers.get_web_page(session, full_url)
    except Exception as e:
        print(e)
        return (
            url,
            discovered_urls,
            False,
            feeds,
            "",
            crawl_depth,
            average_crawl_speed,
            budget_used,
        )

    if page.status_code == 301 or page.status_code == 302 or page.status_code == 308:
        return verify_and_process_helpers.handle_redirect(
            url,
            discovered_urls,
            False,
            feeds,
            "",
            crawl_depth,
            average_crawl_speed,
            budget_used,
        )

    if len(average_crawl_speed) > 10 and page.elapsed.total_seconds() > 2:
        write_log(
            "WARNING: {} took {} seconds to load, server slow".format(
                full_url, page.elapsed.total_seconds()
            ),
            site,
        )

    average_crawl_speed.append(page.elapsed.total_seconds())

    # only store the most recent 100 times
    average_crawl_speed = average_crawl_speed[:100]

    try:
        page_html_contents = BeautifulSoup(page.content, "html.parser")
    except Exception as e:
        print(e)
        page_html_contents = BeautifulSoup(page.content, "html5lib")

    # don't index pages that are likely to be 404s
    is_soft_404 = detect_soft_404(page_html_contents)

    if is_soft_404:
        return (
            url,
            {},
            False,
            feeds,
            None,
            crawl_depth,
            average_crawl_speed,
            budget_used,
        )

    # get body of page
    body = page_html_contents.find("body")

    # get hash of web page
    hash = hashlib.sha256(str(body).encode("utf-8")).hexdigest()

    if web_page_hashes.get(hash) and web_page_hashes.get(hash) != full_url:
        write_log(
            "{} has already been indexed (hash the same as {}), skipping".format(
                full_url, web_page_hashes.get(hash)
            ),
            site,
        )
        return (
            url,
            {},
            False,
            feeds,
            hash,
            crawl_depth,
            average_crawl_speed,
            budget_used,
        )

    # if http-equiv refresh redirect present
    # not recommended by W3C but still worth checking for just in case
    verify_and_process_helpers.check_meta_equiv_refresh(
        url,
        feeds,
        hash,
        crawl_depth,
        average_crawl_speed,
        page_html_contents,
        discovered_urls,
        full_url,
    )

    # check for canonical url

    if page_html_contents.find("link", {"rel": "canonical"}):
        canonical_url = page_html_contents.find("link", {"rel": "canonical"}).get(
            "href"
        )

        canonical = find_base_url_path(canonical_url)

        # is_canonical = url_handling_helpers.parse_canonical(
        #     canonical, full_url, canonical_url, crawl_queue, discovered_urls
        # )

        # if is_canonical:
        #     return (
        #         url,
        #         discovered_urls,
        #         False,
        #         feeds,
        #         hash,
        #         crawl_depth,
        #         average_crawl_speed,
        #         budget_used,
        #     )

    try:
        noindex, nofollow_all = verify_and_process_helpers.check_if_url_is_noindexed(
            page_html_contents, full_url
        )
    except Exception as e:
        print(e)
        return (
            url,
            discovered_urls,
            False,
            feeds,
            hash,
            crawl_depth,
            average_crawl_speed,
            budget_used,
        )

    links = filter_nofollow_links(page_html_contents, nofollow_all)

    # filter out pages marked as adult content
    try:
        verify_and_process_helpers.filter_adult_content(page_html_contents, full_url)
    except Exception as e:
        print(e)
        return (
            url,
            discovered_urls,
            False,
            feeds,
            hash,
            crawl_depth,
            average_crawl_speed,
            budget_used,
        )

    # only discover feeds and new links if a crawl is going on
    # this is used to ensure that the crawler doesn't discover new links or feeds when just indexing one page from a site that is already in the index
    if link_discovery:
        feeds, feed_urls = verify_and_process_helpers.link_discovery_processing(
            page, site, full_url, feeds, feed_urls
        )

        (
            final_urls,
            crawl_queue,
            all_links,
            external_links,
            discovered_urls,
        ) = page_link_discovery.page_link_discovery(
            links,
            final_urls,
            crawl_queue,
            full_url,
            all_links,
            external_links,
            discovered_urls,
            site_url,
            crawl_depth,
        )

    try:
        verify_and_process_helpers.initial_url_checks(full_url)
    except Exception as e:
        print(e)
        url_handling_helpers.check_remove_url(full_url)
        return (
            url,
            discovered_urls,
            False,
            feeds,
            hash,
            crawl_depth,
            average_crawl_speed,
            budget_used,
        )

    page_text = verify_and_process_helpers.get_main_page_text(page_html_contents)

    if page_text is None:
        return (
            url,
            discovered_urls,
            False,
            feeds,
            hash,
            crawl_depth,
            average_crawl_speed,
            budget_used,
        )

    heading_info = {"h1": [], "h2": [], "h3": [], "h4": [], "h5": [], "h6": []}

    for k, v in heading_info.items():
        if page_text.find_all(k):
            for h in page_text.find_all(k):
                v.append(h.text)

    # only get first five of each heading
    for k, v in heading_info.items():
        if len(v) > 5:
            v = v[:5]

    # Only index if noindex attribute is not present

    (
        published_on,
        meta_description,
        doc_title,
        noindex,
    ) = crawler.page_info.get_page_info(
        page_html_contents, full_url, homepage_meta_description
    )

    doc_title = verify_and_process_helpers.remove_repeated_fragments_from_title(
        doc_title, home_page_title
    )

    if noindex:
        url_handling_helpers.check_remove_url(full_url)
        return (
            url,
            discovered_urls,
            False,
            feeds,
            hash,
            crawl_depth,
            average_crawl_speed,
            budget_used,
        )

    # get number of links

    links = page_html_contents.find_all("a")

    number_of_links = len(links)
    word_count = len(page_html_contents.get_text().split())

    thin_content = check_if_content_is_thin(word_count, number_of_links)

    # tags to remove happens here so that valuable content can still be extracted
    # (i.e. links from nav bars)
    TAGS_TO_REMOVE = [
        "script",
        "style",
        "noscript",
        "iframe",
        "frame",
        "object",
        "footer",
        "nav",
        "aside",
    ]

    for tag in TAGS_TO_REMOVE:
        # remove tags that are not likely to be useful
        for match in body.find_all(tag):
            match.decompose()

    calculate_links.get_all_links(url, nofollow_all, page_html_contents)

    try:
        pages_indexed = save_record.save_to_file(
            full_url,
            published_on,
            doc_title,
            meta_description,
            heading_info,
            page,
            pages_indexed,
            page_html_contents,
            len(links),
            crawl_budget,
            nofollow_all,
            page_html_contents.find("body"),
            h_card,
            hash,
            thin_content,
            elasticsearch_client,
        )
    except Exception as e:
        # write_log(e)
        print(e)
        raise Exception

    return (
        url,
        discovered_urls,
        True,
        feeds,
        hash,
        crawl_depth,
        average_crawl_speed,
        budget_used,
    )
