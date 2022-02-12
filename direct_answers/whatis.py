from typing import Any, Dict, Tuple

from bs4 import BeautifulSoup

from .structures import DirectAnswer


def parse_what_is(
    original_cleaned_value: str, soup: BeautifulSoup, url: str
) -> DirectAnswer:
    """
    Answer a "what is" query using the text on a web page.

    :param original_cleaned_value: The original cleaned query value.
    :param soup: The BeautifulSoup object of the post.
    :param url: The URL of the post.

    :return: A DirectAnswer object.
    :rtype: DirectAnswer
    """
    # if "what is" in original_cleaned_value
    if not (
        "what is" in original_cleaned_value
        or "what are" in original_cleaned_value
        or "what were" in original_cleaned_value
        or "microformats" in original_cleaned_value
    ):
        return None, None

    #  if "is a" in p.text.lower() or "are an" in p.text.lower() and original_cleaned_value.lower() in p.text.lower()
    original_cleaned_value = (
        original_cleaned_value.replace("what is", "")
        .replace("what are", "")
        .replace("what were", "")
        .strip()
        .lower()
    )

    p_tags = [
        p.text
        for p in soup.find_all(["p", "span"])
        if ("p-summary" in p.attrs.get("class", []) and p.text is not None)
        or f"{original_cleaned_value} is" in p.text.lower()
        or f"{original_cleaned_value} are" in p.text.lower()
    ]

    if soup.find("h1"):
        title = soup.find("h1").text
    elif soup.find("title"):
        title = soup.find("title").text
    else:
        title = "IndieWeb"

    if len(p_tags) > 0:
        html = (f"<p>{p_tags[0]}</p>",)

        return DirectAnswer(
            answer_html=html,
            answer_type="direct_answer",
            breadcrumb=url,
            title=title,
        )

    return None, None
