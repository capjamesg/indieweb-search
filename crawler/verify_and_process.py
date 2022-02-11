import datetime
import hashlib
import logging
from urllib.parse import urlparse as parse_url

import indieweb_utils
from bs4 import BeautifulSoup

import crawler.add_to_database as add_to_database
import crawler.discovery as page_link_discovery
import crawler.page_info
import crawler.url_handling_helpers as url_handling_helpers
import crawler.verify_and_process_helpers as verify_and_process_helpers

yesterday = datetime.datetime.today() - datetime.timedelta(days=1)


def find_base_url_path(url):
    """
    Finds the base path of a URL.
    """
    url = url.strip("/").replace("http://", "https://").split("?")[0].lower()

    return url


def filter_nofollow_links(page_desc_soup, nofollow_all):
    if nofollow_all is False:
        links = [
            l
            for l in page_desc_soup.find_all("a")
            if (l.get("rel") and "nofollow" not in l["rel"])
            or (not l.get("rel") and l.get("href") not in ["#", "javascript:void(0);"])
        ]
    else:
        links = []

    return links


def check_if_content_is_thin(word_count, number_of_links):
    thin_content = False

    # if the ratio of words to links < 3:1, do not index
    # these pages may be spam or other non-content pages that will not be useful to those using the search engine
    # also filter out pages with 400 words or less
    if (
        word_count
        and (word_count > 0 and number_of_links and number_of_links > 0)
        and word_count > 200
        and word_count / number_of_links < 3
    ) or (word_count < 400):
        thin_content = True

    return thin_content


def crawl_urls(
    final_urls,
    namespaces_to_ignore,
    pages_indexed,
    all_links,
    external_links,
    discovered_urls,
    iterate_list_of_urls,
    site_url,
    crawl_budget,
    url,
    feeds,
    feed_urls,
    site,
    session,
    web_page_hashes,
    average_crawl_speed,
    homepage_meta_description,
    link_discovery=True,
    h_card=[],
    crawl_depth=0,
):
    """
    Crawls URLs in list, adds URLs to index, and returns updated list.
    """

    feeds = []

    # make sure urls with // are processed correctly
    # example: https://www.test.com//text.html should become https://www.test.com/text.html
    parsed_url = parse_url(url)
    url_domain = parsed_url.netloc
    url_path = parsed_url.path

    full_url = indieweb_utils.canonicalize_url(url, url_domain).lower()

    verify_and_process_helpers.initial_url_checks(
        full_url, feeds, crawl_depth, average_crawl_speed, url
    )

    # Only get URLs that match namespace exactly
    in_matching_namespace = [
        s for s in namespaces_to_ignore if s.startswith(url_path) or s == url_path
    ]

    # The next line of code skips indexing namespaces excluded in robots.txt
    if len(in_matching_namespace) > 0:
        return url, discovered_urls, True, feeds, "", crawl_depth, average_crawl_speed

    session.max_redirects = 3

    page_test, nofollow_all = verify_and_process_helpers.initial_head_request(
        full_url, feeds, crawl_depth, average_crawl_speed, url, session, site_url
    )

    has_canonical = verify_and_process_helpers.parse_link_headers(
        page_test, full_url, iterate_list_of_urls, discovered_urls
    )

    if has_canonical == True:
        return (
            url,
            discovered_urls,
            False,
            None,
            crawl_depth,
            average_crawl_speed,
        )

    try:
        page = verify_and_process_helpers.get_web_page(session, full_url)
    except:
        return url, {}, False, feeds, None, crawl_depth, average_crawl_speed

    if page.status_code == 301 or page.status_code == 302 or page.status_code == 308:
        return verify_and_process_helpers.handle_redirect(
            page,
            final_urls,
            iterate_list_of_urls,
            url,
            feeds,
            crawl_depth,
            average_crawl_speed,
            discovered_urls,
            full_url,
        )

    if len(average_crawl_speed) > 10 and page.elapsed.total_seconds() > 2:
        print(
            "WARNING: {} took {} seconds to load, server slow".format(
                full_url, page.elapsed.total_seconds()
            )
        )

    average_crawl_speed.append(page.elapsed.total_seconds())

    print(f"{full_url} took {page.elapsed.total_seconds()} seconds to load")

    # only store the most recent 100 times
    average_crawl_speed = average_crawl_speed[:100]

    try:
        page_desc_soup = BeautifulSoup(page.content, "html.parser")
    except:
        page_desc_soup = BeautifulSoup(page.content, "html5lib")

    # get body of page
    body = page_desc_soup.find("body")

    # get hash of web page
    hash = hashlib.sha256(str(body).encode("utf-8")).hexdigest()

    if web_page_hashes.get(hash):
        print(
            "{} has already been indexed (hash the same as {}), skipping".format(
                full_url, web_page_hashes.get(hash)
            )
        )
        return url, {}, False, feeds, hash, crawl_depth, average_crawl_speed

    # if http-equiv refresh redirect present
    # not recommended by W3C but still worth checking for just in case
    verify_and_process_helpers.check_meta_equiv_refresh(
        url,
        feeds,
        hash,
        crawl_depth,
        average_crawl_speed,
        page_desc_soup,
        discovered_urls,
        full_url,
    )

    # check for canonical url

    if page_desc_soup.find("link", {"rel": "canonical"}):
        canonical_url = page_desc_soup.find("link", {"rel": "canonical"}).get("href")

        canonical = find_base_url_path(canonical_url)

        is_canonical = url_handling_helpers.parse_canonical(
            canonical, full_url, canonical_url, iterate_list_of_urls, discovered_urls
        )

        if is_canonical:
            return url, discovered_urls, False, None, crawl_depth, average_crawl_speed

    try:
        noindex, nofollow_all = verify_and_process_helpers.check_if_url_is_noindexed(
            page_desc_soup, full_url
        )
    except:
        return (
            url,
            discovered_urls,
            False,
            feeds,
            hash,
            crawl_depth,
            average_crawl_speed,
        )

    links = filter_nofollow_links(page_desc_soup, nofollow_all)

    # filter out pages marked as adult content
    try:
        verify_and_process_helpers.filter_adult_content(page_desc_soup, full_url)
    except:
        return (
            url,
            discovered_urls,
            False,
            feeds,
            hash,
            crawl_depth,
            average_crawl_speed,
        )

    # only discover feeds and new links if a crawl is going on
    # this is used to ensure that the crawler doesn't discover new links or feeds when just indexing one page from a site that is already in the index
    if link_discovery:
        feeds, feed_urls = verify_and_process_helpers.link_discovery_processing(
            page, site, full_url, feeds, feed_urls
        )

        (
            final_urls,
            iterate_list_of_urls,
            all_links,
            external_links,
            discovered_urls,
        ) = page_link_discovery.page_link_discovery(
            links,
            final_urls,
            iterate_list_of_urls,
            full_url,
            all_links,
            external_links,
            discovered_urls,
            site_url,
            crawl_depth,
        )

    page_text, thin_content = verify_and_process_helpers.get_main_page_text(
        page_desc_soup
    )

    if page_text is None:
        return (
            url,
            discovered_urls,
            False,
            feeds,
            hash,
            crawl_depth,
            average_crawl_speed,
        )

    heading_info = {"h1": [], "h2": [], "h3": [], "h4": [], "h5": [], "h6": []}

    for k, v in heading_info.items():
        if page_text.find_all(k):
            for h in page_text.find_all(k):
                v.append(h.text)

    # Only index if noindex attribute is not present

    (
        page_text,
        page_desc_soup,
        published_on,
        meta_description,
        doc_title,
        noindex,
    ) = crawler.page_info.get_page_info(
        page_text, page_desc_soup, full_url, homepage_meta_description
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
        )

    # get number of links

    links = page_desc_soup.find_all("a")
    number_of_links = len(links)
    word_count = len(page_desc_soup.get_text().split())

    thin_content = check_if_content_is_thin(word_count, number_of_links)

    try:
        pages_indexed = add_to_database.add_to_database(
            full_url,
            published_on,
            doc_title,
            meta_description,
            heading_info,
            page,
            pages_indexed,
            page_desc_soup,
            len(links),
            crawl_budget,
            nofollow_all,
            page_desc_soup.find("body"),
            h_card,
            hash,
            thin_content,
        )
    except Exception as e:
        print(e)
        logging.warning(f"error with {full_url}")
        logging.warning(e)

    return url, discovered_urls, True, feeds, hash, crawl_depth, average_crawl_speed
