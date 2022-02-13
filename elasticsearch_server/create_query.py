def assemble_query(
    query: str,
    category: str,
    contains_js: str,
    inurl: str,
    mf2_property: str,
    site: str,
) -> str:
    query = query.replace("what is ", "").replace("who is ", "")

    query = query.strip().replace(" ", " AND ").strip("AND").strip()

    final_query = ""

    if len(query) > 0:
        for w in range(0, len(query.split(" "))):
            final_query += query.split(" ")[w]

        if site and len(site) > 0:
            query = query + f" AND (url:{site})"
        elif site and len(site) == 0:
            query = f"(url:{site})"

        if inurl and len(inurl) > 0:
            query = query + f" AND (url:{inurl})"
        elif inurl and len(inurl) == 0:
            query = f"(url:{inurl})"
    else:
        if site and len(site) > 0:
            query = query + f"(url:{site})"
        elif site and len(site) == 0:
            query = f"(url:{site})"

        if inurl and len(inurl) > 0:
            query = query + f"(url:{inurl})"
        elif inurl and len(inurl) == 0:
            query = f"(url:{inurl})"

    if contains_js and contains_js == "false":
        query = query + " AND (js:false)"

    if category:
        category_list = category.split(",")
        category_string = f" (AND (category:{category_list}) OR".strip(" OR") + ")"

        query = query + category_string

    if mf2_property:
        mf2_property_list = mf2_property.split(",")
        mf2_property_string = (
            f" (AND (mf2_property:{mf2_property_list}) OR".strip(" OR") + ")"
        )

        query = query + mf2_property_string

    valid_post_types = [
        ("rsvp", "rsvp"),
        ("reply", "reply"),
        ("replies", "reply"),
        ("repost", "repost"),
        ("share", "repost"),
        ("like", "like"),
        ("video", "video"),
        ("note", "note"),
        ("article", "article")
    ]

    last_query_word = query.split(" ")[-1]

    for name, collection_identifier in valid_post_types:
        if last_query_word == name or last_query_word == name + "s":
            final_query = final_query + f" AND (post_type:{collection_identifier})"
            break

    return query
