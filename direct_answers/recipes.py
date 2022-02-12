from typing import Any, Dict, Tuple

from bs4 import BeautifulSoup

from .structures import DirectAnswer


def parse_recipe(
    original_cleaned_value: str, soup: BeautifulSoup, url: str, post: dict
) -> DirectAnswer:
    """
    Get information about a recipe.

    :param original_cleaned_value: The original cleaned value.
    :param soup: The BeautifulSoup object of the post.
    :param url: The URL of the post.
    :param post: The post object.

    :return: A DirectAnswer object.
    :rtype: DirectAnswer
    """
    if not "recipe" in original_cleaned_value:
        return None, None

    h_recipe = soup.select(".h-recipe")

    if not h_recipe:
        return None, None

    h_recipe = h_recipe[0]

    name = h_recipe.select(".p-name")

    if not name:
        name = soup.find("title")

    ingredients = ["<li>" + x.text + "</li>" for x in h_recipe.select(".p-ingredient")]

    instructions = h_recipe.select(".e-instructions")[0].find_all("li")

    instructions = ["<li>" + x.text + "</li>" for x in instructions]

    if len(ingredients) > 0 and len(instructions) > 0:
        html = "<h3>Ingredients</h3><p>{}</p><h3>Instructions</h3><p>{}</p>".format(
            "".join(i for i in ingredients), "".join(i for i in instructions)
        )

        return DirectAnswer(
            answer_html=html,
            answer_type="direct_answer",
            breadcrumb=url,
            title=post["title"],
        )

    return None
