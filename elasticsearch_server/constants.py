# values not to send to clients that may be stored in the index
# a lot of the values in to_delete are deprecated or were never fully implemented
to_delete = [
    "length",
    "outgoing_links",
    "favicon",
    "http_headers",
    "page_is_nofollow",
    "h_card",
    "category",
    "page_rank",
    "md5_hash",
    "important_phrases",
]

default_fields = [
    "title^1.4",
    "description^0.4",
    "url^0.2",
    "category^0.4",
    "published^0",
    "keywords^0",
    "text^1.8",
    "h1^1.7",
    "h2^0.5",
    "h3^0.5",
    "h4^0.5",
    "h5^0.75",
    "h6^0.25",
    "domain^2",
]
