from bs4 import BeautifulSoup

from .structures import DirectAnswer


def get_code_snippet(
    original_cleaned_value: str, soup: BeautifulSoup, post: dict, url: str
) -> DirectAnswer:
    """
    Get a code snippet from a post that relates to a query.

    :param original_cleaned_value: The original cleaned value of the query.
    :param soup: The BeautifulSoup object of the post.
    :param post: The post object.
    :param url: The URL of the post.

    :return: A DirectAnswer object.
    :rtype: DirectAnswer
    """
    if not "code" in original_cleaned_value and not "markup" in original_cleaned_value:
        return None

    if not "<pre>" in post["page_content"] and "<em>" not in post["page_content"]:
        return None

    # get all pre tags

    pre_tags = soup.find_all("pre")

    for tag in pre_tags:
        # if paragraph before mentions term
        tag_before = tag.find_previous_sibling("p")
        # get tag before the last one
        if tag_before and tag_before.text:
            tag_before_last = tag_before.find_previous_sibling("p")
            heading_before = tag.find_previous_sibling("h2")
            context = (
                "<h2>"
                + heading_before.text
                + "</h2>"
                + "<p>"
                + tag_before_last.text
                + "</p>"
                + "<p>"
                + tag_before.text
                + "</p>"
            )
        elif tag.text:
            context = "<p>" + tag.text + "</p>"

        return DirectAnswer(
            answer_html=tag.text,
            answer_type="code",
            breadcrumb=url,
            title=post["title"],
            context=context,
        )

    return None
