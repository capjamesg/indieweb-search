import datetime
import random

import nltk
import spacy
from bs4 import BeautifulSoup

from . import (definition, events, get_answer_to_question, process_entity_type,
               recipes, reviews, whatis, whois, aeropress_recipe)
from .code_snippets import get_code_snippet
from .entity_type_map import entity_types
from .structures import DirectAnswer


def generate_featured_snippet(
    cleaned_value: str,
    special_result: str,
    nlp: spacy,
    url: str = None,
    post: dict = None,
) -> DirectAnswer:
    """
    Clean a query and then a direct answer to a post by calling all specialist direct answer functions (stored in the direct_answers/ folder).

    :param cleaned_value: The cleaned value from the searcher's query.
    :param special_result: The special result from the searcher's query (if one has already been generated).
    :param nlp: The spacy object.
    :param url: The URL of the post.
    :param post: The post object.

    :return: A DirectAnswer object.
    :rtype: DirectAnswer
    """
    # Generate a featured snippet for the search result
    if url is None:
        return "", special_result

    original_url = url

    if "who is" in cleaned_value:
        url = url.replace("https://", "").replace("http://", "").split("/")[0]

    original_cleaned_value = cleaned_value.lower()

    new_cleaned_value_for_direct_answer = " ".join(
        [
            w
            for w in cleaned_value.split(" ")
            if w not in nltk.corpus.stopwords.words("english") or w in ["why", "how"]
        ]
    ).strip()

    proper_nouns = [
        word.lower()
        for word, pos in nltk.tag.pos_tag(post["title"].split())
        if pos == "NNP"
    ]

    # remove all proper nouns from cleaned_value

    cleaned_value = " ".join(
        [
            w
            for w in cleaned_value.split(" ")
            if w.lower() not in proper_nouns
            and w.lower() not in post["title"].lower().split()
            and w.lower() not in post["url"].lower().split("/")[-1]
        ]
    )

    # read post with bs4
    if post.get("page_content"):
        soup = BeautifulSoup(post["page_content"], "lxml")
    else:
        return "", special_result

    response = get_code_snippet(original_cleaned_value, soup, post, url)

    if response != None:
        return response

    response = recipes.parse_recipe(original_cleaned_value, soup, url, post)

    if response != (None, None):
        return response

    response = reviews.parse_review(original_cleaned_value, soup, url, post)

    if response != (None, None):
        return response

    response = events.parse_event(original_cleaned_value, soup, url, post)

    if response != (None, None):
        return response

    response = whatis.parse_what_is(original_cleaned_value, soup, url)

    if response != (None, None):
        return response

    response = whois.parse_whois(original_cleaned_value, soup, url, original_url)

    if response != (None, None):
        return response

    response = whois.parse_social(original_cleaned_value, soup, url, original_url)

    if response != (None, None):
        return response

    response = whois.parse_get_rel(original_cleaned_value, soup, original_url)

    if response != (None, None):
        return response

    response = whois.parse_feed(original_cleaned_value, soup, url)

    if response != (None, None):
        return response

    response = whois.parse_address(original_cleaned_value, soup, url)

    if response != (None, None):
        return response

    response = definition.get_term_definition(
        soup, url, new_cleaned_value_for_direct_answer, post
    )

    if response != (None, None):
        return response

    # check if cleaned value refers to an ent type
    response = process_entity_type.get_entity_response(
        cleaned_value, entity_types, soup, nlp, url, post
    )

    if response != (None, None):
        return response

    # look for the answer to a question
    response = get_answer_to_question.retrieve_answer(
        soup,
        original_cleaned_value,
        cleaned_value,
        new_cleaned_value_for_direct_answer,
        post,
        url,
    )

    return response
