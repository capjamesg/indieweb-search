import spacy

from .structures import DirectAnswer


def get_entity_response(
    cleaned_value: str, entity_types: dict, soup: str, nlp: spacy, url: str, post: dict
) -> DirectAnswer:
    """
    Search for pre-programmed entity types (defined in entity_type_map.py) in the post and retrieve context around the entity.

    :param cleaned_value: The original cleaned value of the query.
    :param entity_types: The entity types to search for.
    :param soup: The BeautifulSoup object of the post.
    :param nlp: The spacy object of the post.
    :param url: The URL of the post.

    :return: A DirectAnswer object.
    :rtype: DirectAnswer
    """
    entity_type = "NONE"

    for word in cleaned_value.split(" "):
        if entity_types.get(word.lower()):
            entity_type = entity_types.get(word.lower())
            if entity_type == "GPE":
                all_locations = [
                    w
                    for w in nlp(
                        " ".join(soup.get_text().replace("\n", ". ").split(". "))
                    ).ents
                    if w.label_ == "GPE" and "in" in w.text
                ]
                if len(all_locations) > 0:
                    all_locations = all_locations[0]
            break

    if entity_type != "NONE":
        sentence_with_query = [
            s
            for s in soup.get_text().replace("\n", ". ").split(". ")
            if all(x in s.lower() for x in cleaned_value.strip().split(" "))
        ]

        if len(sentence_with_query) > 0:
            ents = [
                w for w in nlp(sentence_with_query[0]).ents if w.label_ == entity_type
            ]

            if len(ents) > 0:
                return "<b style='font-size: 22px'>{}</b><br>{}".format(
                    ", ".join([e.text for e in ents]),
                    sentence_with_query[0].replace("\n", " "),
                ), {
                    "type": "direct_answer",
                    "breadcrumb": url,
                    "title": soup.find("h1").text,
                    "featured_image": post.get("featured_image"),
                }
            elif len(all_locations) > 0:
                return "<b style='font-size: 22px'>{}</b><br>{}".format(
                    all_locations[0].text, sentence_with_query[0]
                ), {
                    "type": "direct_answer",
                    "breadcrumb": url,
                    "title": soup.find("h1").text,
                    "featured_image": post.get("featured_image"),
                }
