from bs4 import BeautifulSoup

from .structures import DirectAnswer


def get_term_definition(
    soup: BeautifulSoup, url: str, new_cleaned_value_for_direct_answer: str, post: dict
) -> DirectAnswer:
    """
    Get the definition for a term by looking for a <dfn> tag.

    :param soup: The BeautifulSoup object of the post.
    :param url: The URL of the post.
    :param new_cleaned_value_for_direct_answer: The cleaned value from the searcher's query.
    :param post: The post object.

    :return: A DirectAnswer object.
    :rtype: DirectAnswer
    """
    if not soup.find_all("dfn"):
        return None

    for dfn in soup.find_all("dfn"):
        if (
            dfn.text.lower().replace(" ", "").replace("-", "")
            == new_cleaned_value_for_direct_answer.lower()
            .replace(" ", "")
            .replace("-", "")
            or "define" in new_cleaned_value_for_direct_answer.lower()
        ):

            html = "<b style='font-size: 22px'>{}</b><br>{}".format(
                dfn.text, dfn.find_parent("p").text
            )

            return DirectAnswer(
                answer_html=html,
                answer_type="direct_answer",
                breadcrumb=url,
                title=post["title"],
                featured_image=post.get("featured_image"),
            )

    return None
