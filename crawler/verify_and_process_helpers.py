import datetime

import requests

import config
import crawler.find_base_url_path as find_base_url_path
import crawler.url_handling_helpers as url_handling_helpers


def parse_link_headers(page_test, full_url, iterate_list_of_urls, discovered_urls):
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

        canonical = find_base_url_path(link["rel"])

        result = url_handling_helpers.parse_canonical(
            canonical,
            full_url,
            link["url"],
            iterate_list_of_urls,
            discovered_urls,
        )

        if result:
            return True

    return False


def check_for_redirect_url(page_test, full_url, site_url):
    if (
        page_test.history
        and page_test.history[-1].url
        and page_test.history[-1].url != full_url
    ):
        # skip redirects to external sites
        if not page_test.history[-1].url.startswith(
            "http://" + site_url
        ) and not page_test.history[-1].url.startswith("https://" + site_url):
            print(
                "{} redirected to {}, which is on a different site, skipping".format(
                    full_url, page_test.history[-1].url
                )
            )
            print(
                "{} redirected to {}, which is on a different site, skipping".format(
                    full_url, page_test.history[-1].url
                )
            )
            raise Exception

        print(f"{full_url} redirected to {page_test.history[-1].url}")

        full_url = page_test.history[-1].url

    return full_url


def initial_url_checks(full_url, feeds, crawl_depth, average_crawl_speed, url):
    if len(full_url) > 125:
        print(f"{full_url} url too long, skipping")
        return url, {}, False, feeds, None, crawl_depth, average_crawl_speed

    if "javascript:" in full_url:
        print(f"{full_url} marked as noindex because it is a javascript resource")
        return url, {}, False, feeds, None, crawl_depth, average_crawl_speed

    if "/wp-json/" in full_url:
        print(f"{full_url} marked as noindex because it is a wordpress api resource")
        return url, {}, False, feeds, None, crawl_depth, average_crawl_speed

    if "?s=" in full_url:
        # print("{} marked as noindex because it is a search result".format(full_url))
        print(f"{full_url} marked as noindex because it is a search result")
        return url, {}, False, feeds, None, crawl_depth, average_crawl_speed

    # there are a few wikis in the crawl and special pages provide very little value to the search index
    if "/Special:" in full_url:
        print(f"{full_url} is a MediaWiki special page, will not crawl")
        return url, {}, False, feeds, hash, crawl_depth, average_crawl_speed

    if "/page/" in full_url and full_url.split("/")[-1].isdigit():
        print(f"{full_url} marked as follow, noindex because it is a page archive")
        url_handling_helpers.check_remove_url(full_url)
        return url, {}, False, feeds, hash, crawl_depth, average_crawl_speed

    if (
        "/tags/" in full_url
        or "/tag/" in full_url
        or "/label/" in full_url
        or "/search/" in full_url
        or "/category/" in full_url
        or "/categories/" in full_url
    ):
        print(
            "{} marked as follow, noindex because it is a tag, label, or search resource".format(
                full_url
            )
        )
        url_handling_helpers.check_remove_url(full_url)
        return url, {}, False, feeds, hash, crawl_depth, average_crawl_speed


def check_if_url_is_noindexed(page_desc_soup, full_url):
    check_if_no_index = page_desc_soup.find("meta", {"name": "robots"})

    if (
        check_if_no_index
        and check_if_no_index.get("content")
        and (
            "noindex" in check_if_no_index.get("content")
            or "none" in check_if_no_index.get("content")
        )
    ):
        print(f"{full_url} marked as noindex, skipping")
        url_handling_helpers.check_remove_url(full_url)
        raise Exception

    elif (
        check_if_no_index
        and check_if_no_index.get("content")
        and "nofollow" in check_if_no_index.get("content")
    ):
        print(
            "all links on {} marked as nofollow due to <meta> robots nofollow value".format(
                full_url
            )
        )
        nofollow_all = True

    return check_if_no_index, nofollow_all


def get_main_page_text(page_desc_soup):
    thin_content = False

    # 20 word minimum will prevent against short notes
    if page_desc_soup.select(".e-content"):
        page_text = page_desc_soup.select(".e-content")[0]
        # print(page_text)
        # if len(page_text.get_text().split(" ")) < 75:
        #     print("content on {} is thin (under 75 words in e-content), marking as thin_content".format(full_url))
        #     print("content on {} is thin (under 75 words in e-content), marking as thin_content".format(full_url))
        #     thin_content = True

    elif page_desc_soup.select(".h-entry"):
        page_text = page_desc_soup.select(".h-entry")[0]
        # print(page_text)
        # if len(page_text.get_text().split(" ")) < 75:
        #     print("content on {} is thin (under 75 words in h-entry), marking as thin_content".format(full_url))
        #     print("content on {} is thin (under 75 words in h-entry), marking as thin_content".format(full_url))
        #     thin_content = True

    elif page_desc_soup.find("main"):
        page_text = page_desc_soup.find("main")
    elif page_desc_soup.find("div", {"id": "main"}):
        page_text = page_desc_soup.find("div", {"id": "main"})
    elif page_desc_soup.find("div", {"id": "app"}):
        page_text = page_desc_soup.find("div", {"id": "app"})
    elif page_desc_soup.find("div", {"id": "page"}):
        page_text = page_desc_soup.find("div", {"id": "page"})
    elif page_desc_soup.find("div", {"id": "site-container"}):
        page_text = page_desc_soup.find("div", {"id": "main"})
    elif page_desc_soup.find("div", {"id": "application-main"}):
        page_text = page_desc_soup.find("div", {"id": "application-main"})
    elif page_desc_soup.find("div", {"id": "site-container"}):
        page_text = page_desc_soup.find("div", {"id": "site-container"})
    else:
        page_text = page_desc_soup.find("body")

    return page_text, thin_content


def initial_head_request(
    full_url, feeds, crawl_depth, average_crawl_speed, url, session, site_url
):
    nofollow_all = False

    try:
        # Check if page is the right content type before indexing
        page_test = session.head(
            full_url, headers=config.HEADERS, allow_redirects=True, verify=False
        )

        # get redirect url
        try:
            full_url = check_for_redirect_url(page_test, full_url, site_url)
        except:
            return url, {}, False, feeds, None, crawl_depth, average_crawl_speed

        if page_test.headers.get("x-robots-tag"):
            # only obey directives pointed at indieweb-search or everyone
            if "indieweb-search:" in page_test.headers.get(
                "x-robots-tag"
            ) or ":" not in page_test.headers.get("x-robots-tag"):
                if "noindex" in page_test.headers.get(
                    "x-robots-tag"
                ) or "none" in page_test.headers.get("x-robots-tag"):
                    print(f"{full_url} marked as noindex")
                    return (
                        url,
                        {},
                        False,
                        feeds,
                        None,
                        crawl_depth,
                        average_crawl_speed,
                    )
                elif "nofollow" in page_test.headers.get("x-robots-tag"):
                    print(
                        "all links on {} marked as nofollow due to x-robots-tag nofollow value".format(
                            full_url
                        )
                    )
                    nofollow_all = True

        content_type_is_valid = verify_content_type_is_valid(page_test, full_url)

        if content_type_is_valid:
            return (
                url,
                {},
                False,
                feeds,
                None,
                crawl_depth,
                average_crawl_speed,
            )

        return page_test, nofollow_all

    except requests.exceptions.Timeout:
        print(f"{full_url} timed out, skipping")
        url_handling_helpers.check_remove_url(full_url)
        return url, {}, False, feeds, None, crawl_depth, average_crawl_speed
    except requests.exceptions.TooManyRedirects:
        print(f"{full_url} too many redirects, skipping")
        url_handling_helpers.check_remove_url(full_url)
        return url, {}, False, feeds, None, crawl_depth, average_crawl_speed
    except:
        print(f"{full_url} failed to connect, skipping")
        return url, {}, False, feeds, None, crawl_depth, average_crawl_speed


def filter_adult_content(page_desc_soup, full_url):
    if page_desc_soup.find("meta", {"name": "rating"}):
        if (
            page_desc_soup.find("meta", {"name": "rating"}).get("content") == "adult"
            or page_desc_soup.find("meta", {"name": "rating"}).get("content")
            == "RTA-5042-1996-1400-1577-RTA"
        ):
            print(f"{full_url} marked as adult content in a meta tag, skipping")
            raise Exception


def verify_content_type_is_valid(page_test, full_url):
    # only index html documents

    if (
        page_test.headers
        and page_test.headers.get("content-type")
        and "text/html" not in page_test.headers["content-type"]
    ):
        url_handling_helpers.check_remove_url(full_url)
        return False

    return True


def check_meta_equiv_refresh(
    url,
    feeds,
    hash,
    crawl_depth,
    average_crawl_speed,
    page_desc_soup,
    discovered_urls,
    full_url,
):
    if page_desc_soup.find("meta", attrs={"http-equiv": "refresh"}):
        refresh_url = (
            page_desc_soup.find("meta", attrs={"http-equiv": "refresh"})["content"]
            .split(";")[1]
            .split("=")[1]
        )

        refresh_domain = refresh_url.split("/")[2]

        if refresh_domain.lower().replace("www.", "") != full_url.split("/")[
            2
        ].lower().replace("www.", ""):
            print(
                "{} has a refresh url of {}, not adding to queue because url points to a different domain".format(
                    full_url, refresh_url
                )
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
    page,
    final_urls,
    iterate_list_of_urls,
    url,
    feeds,
    crawl_depth,
    average_crawl_speed,
    discovered_urls,
    full_url,
):
    redirected_to = page.headers["Location"]

    if redirected_to:
        final_urls[redirected_to] = ""

        iterate_list_of_urls.append(redirected_to)

        # don't index a url if it was redirected from a canonical and wants to redirect again
        if discovered_urls.get(full_url) and discovered_urls.get(full_url).startswith(
            "CANONICAL"
        ):
            split_value = discovered_urls.get(full_url).split(" ")
            redirected_from = split_value[1]
            if redirected_from == redirected_to:
                print(
                    "{} has already been redirected from a canonical url, will not redirect a second time, skipping".format(
                        full_url
                    )
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

    return url, {}, False, feeds


def get_web_page(session, full_url):
    try:
        page = session.get(
            full_url,
            timeout=10,
            headers=config.HEADERS,
            allow_redirects=True,
            verify=False,
        )
    except requests.exceptions.Timeout:
        print(f"{full_url} timed out, skipping")
        raise Exception
    except requests.exceptions.TooManyRedirects:
        print(f"{full_url} too many redirects, skipping")
        url_handling_helpers.check_remove_url(full_url)
        raise Exception
    except:
        print(f"{full_url} failed to connect, skipping")
        raise Exception

    # 404 = not found, 410 = gone
    if page.status_code == 404 or page.status_code == 410:
        raise Exception

    elif page.status_code != 200:
        url_handling_helpers.check_remove_url(full_url)
        print(f"{full_url} page {page.status_code} status code")
        raise Exception

    content_type_is_valid = verify_content_type_is_valid(page, full_url)

    if content_type_is_valid:
        raise Exception

    return page


def link_discovery_processing(page, site, full_url, feeds, feed_urls):
    # check for feed with rel alternate
    # only support rss and atom right now

    # feeds, feed_urls = url_handling_helpers.find_feeds(page_desc_soup, full_url, site)

    # parse link headers
    link_headers = page.headers.get("Link")

    if link_headers:
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

                print(f"{websub_hub} is a websub hub, will save to feeds.json")

            if 'rel="alternate"' in link_header and len(feeds) < 25:
                original_feed_url = (
                    link_header.split(";")[0].strip().strip("<").strip(">").lower()
                )

                if original_feed_url and original_feed_url not in feed_urls:
                    # get feed type
                    if 'type="' in link_header:
                        feed_type = link_header.split('type="')[1].split('"')[0]
                    else:
                        feed_type = "feed"

                    if original_feed_url.startswith("/"):
                        # get site domain
                        domain = full_url.split("/")[2]
                        feed_url = (
                            full_url.split("/")[0] + "//" + domain + original_feed_url
                        )

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
                            and original_feed_url.split("/")[2]
                            == full_url.split("/")[2]
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
