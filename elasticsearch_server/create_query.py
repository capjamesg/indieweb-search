def assemble_query(query, category, contains_js, inurl, mf2_property, site):
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

    return query
