def get_default_search_param(query: str, fields: str) -> dict:
    search_param = {
        # use script to calculate score
        "query": {
            "script_score": {
                "query": {
                    "query_string": {
                        "query": query,
                        "fields": fields,
                        "minimum_should_match": "3<75%",
                    },
                },
                "script": {
                    "source": """
                        return _score + Math.log((1 + (doc['incoming_links'].value)) * 5);
                    """
                },
            },
        },
    }

    return search_param


def get_date_ordered_query(query: str, order: str) -> dict:
    search_param = {
        "query": {
            "query_string": {
                "query": query,
                "fields": [
                    "title^2",
                    "description^1.5",
                    "url^1.3",
                    "category^0",
                    "published_on^0",
                    "keywords^0",
                    "text^2.8",
                    "h1^1.7",
                    "h2^1.5",
                    "h3^1.2",
                    "h4^0.5",
                    "h5^0.75",
                    "h6^0.25",
                    "domain^3",
                ],
                "minimum_should_match": "3<75%",
            },
        },
        "sort": [{"published_on.keyword": {"order": order}}],
    }

    return search_param


def get_auto_suggest_query(query: str) -> dict:
    search_param = {
        "suggest": {
            "text": query,
            "simple_phrase": {
                "phrase": {
                    "field": "title",
                    "size": 8,
                    "gram_size": 3,
                    "direct_generator": [{"field": "title", "suggest_mode": "always"}],
                    "highlight": {"pre_tag": "<em>", "post_tag": "</em>"},
                }
            },
        }
    }

    return search_param
