# implementation of the post type discovery spec
# see spec on the IndieWeb wiki: https://indieweb.org/post-type-discovery

def get_post_type(h_entry):
    post = h_entry.get("properties")

    if post == None:
        return "unknown"

    values_to_check = [
        ("rsvp", "rsvp"),
        ("in-reply-to", "reply"),
        ("repost-of", "repost"),
        ("like-of", "like"),
        ("video", "video"),
        ("photo", "photo"),
        ("summary", "summary")
    ]

    for item in values_to_check:
        if post.get(item[0]):
            return item[1]

    post_type = "note"

    if post.get("name") == None or post.get("name")[0] == "":
        return post_type

    title = post.get("name")[0].strip().replace("\n", " ").replace("\r", " ")

    content = post.get("content")

    if content and content[0] != "":
        content = content[0].strip().replace("\n", " ").replace("\r", " ")

    if not content.startswith(title):
        return "article"

    return "note"