from bs4 import BeautifulSoup

from .structures import DirectAnswer


def parse_review(
    original_cleaned_value: str, soup: BeautifulSoup, url: str, post: dict
) -> DirectAnswer:
    """
    Get review information from a web page.

    :param original_cleaned_value: The original cleaned value.
    :param soup: The BeautifulSoup object of the post.
    :param url: The URL of the post.
    :param post: The post object.

    :return: A DirectAnswer object.
    :rtype: DirectAnswer
    """
    if not "review" in original_cleaned_value:
        return None, None

    h_review = soup.select(".h-review")

    if h_review:
        return None

    h_review = h_review[0]

    name = h_review.select(".p-name")[0].text

    if not name:
        name = soup.find("title")

    rating = h_review.select(".p-rating")

    if not rating:
        rating = h_review.select(".rating")[0].text

    if not rating:
        rating = ""

    review = h_review.select(".e-content")

    if review:
        # only show first four sentences of review
        review = ". ".join(review[0].text.split(". ")[:4]) + "..."
    else:
        review = ""

    html = f"<h3>Review of {name}</h3><p>Rating: {rating}</p><p>{review}</p>"

    return DirectAnswer(
        answer_html=html,
        answer_type="direct_answer",
        breadcrumb=url,
        title=post["title"],
    )


def parse_aggregate_review(
    original_cleaned_value: str, soup: BeautifulSoup, url: str, post: dict
) -> DirectAnswer:
    """
    Get an aggregate review from a web page by searching for the h-review-aggregate class.

    :param original_cleaned_value: The original cleaned value.
    :param soup: The BeautifulSoup object of the post.
    :param url: The URL of the post.

    :return: A DirectAnswer object.
    :rtype: DirectAnswer
    """
    if not "aggregate review" in original_cleaned_value:
        return None, None

    h_review = soup.select(".h-review-aggregate")

    if not h_review:
        return None, None

    h_review = h_review[0]

    to_show = ""

    if not h_review.select(".p-item"):
        return None, None

    to_show += "<p>" + h_review.select(".p-item")[0].text + "</p>"

    supported_properties = [
        "p-average",
        "p-best",
        "p-worst",
        "p-count",
        "p-votes",
    ]

    for property in supported_properties:
        if h_review.select(f".{property}"):
            to_show += "<li><b>{}</b>{}</li>".format(
                property.replace("p-", "").title(),
                h_review.select(".{}".format(property))[0].text,
            )

    html = "<h3>Aggregate review of {}</h3><ul>{}</ul>".format(to_show)

    return DirectAnswer(
        answer_html=html,
        answer_type="direct_answer",
        breadcrumb=url,
        title=post["title"],
    )
