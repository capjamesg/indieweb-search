import requests

from config import ROOT_DIRECTORY


def run_test_queries():
    queries = [
        "coffee",
        "steampunk",
        "obadiah",
        "chemex",
        "aeropress recipe",
        "indieweb",
        "build a website",
        "cold brew",
        "PuckPuck",
        "speciality coffee",
        "accessibility",
        'web category:"IndieWeb"',
        'aeropress category:"Coffee" before:"2021-05-10"',
    ]

    with open(ROOT_DIRECTORY + "/data/test_queries.md", "w+") as f:
        for q in queries:
            r = requests.get(
                f'https://search.jamesg.blog/results?query="{q}"&json=true'
            )

            to_show = [f"{item[0]} - {item[2]}" for item in r.json()]

            f.write(f"**First results page for '{q}' query**\n\n")
            for item in to_show:
                f.write(f"- {item}\n")
