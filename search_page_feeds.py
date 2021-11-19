from flask import jsonify

def process_h_card(row):
    item = {
        "type": "card",
    }

    if row["_source"]["h_card"].get("name"):
        item["name"] = row["_source"]["h_card"]["name"][0]
    
    if row["_source"]["h_card"].get("url"):
        item["url"] = row["_source"]["h_card"]["url"][0]

    if row["_source"]["h_card"].get("photo"):
        item["photo"] = row["_source"]["h_card"]["photo"][0]

    return item

def process_json_feed(rows, cleaned_value, page, format):
    result = []

    author = {
        "name": "IndieWeb Search",
        "url": "https://es-indieweb-search.jamesg.blog",
        "avatar": "https://es-indieweb-search.jamesg.blog/favicon.ico"
    }

    for row in rows:
        item = {
            "id": row["_source"]["url"],
            "url": row["_source"]["url"],
            "title": row["_source"]["title"],
            "content_html": row["_source"]["page_content"],
            "content_text": row["_source"]["page_text"],
            "date_published": row["_source"]["published_on"],
        }

        if row["_source"]["h_card"]:
            item["author"] = process_h_card(row)

            if item["author"].get("photo"):
                item["author"]["avatar"] = item["author"]["photo"]
                del item["author"]["photo"]

        result.append(item)

    final_feed = {
        "feed_url": "https://es-indieweb-search.jamesg.blog/results?query={}&page={}&format={}".format(cleaned_value, page, format),
        "title": "IndieWeb Search Results for {}".format(cleaned_value),
        "home_page_url": "https://es-indieweb-search.jamesg.blog",
        "author": author,
        "items": result
    }

    return jsonify(final_feed)

def process_jf2_feed(rows):
    results = []

    for row in rows:
        item = {
            "type": "entry",
            "post-type": "entry",
            "published": row["_source"]["published_on"],
            "url": row["_source"]["url"],
            "title": row["_source"]["title"],
            "content": {
                "text": row["_source"]["page_text"],
                "html": row["_source"]["page_content"]
            }
        }

        if row["_source"]["h_card"]:
            item["author"] = process_h_card(row)

        results.append(item)

    return jsonify({"type": "feed", "items": results})