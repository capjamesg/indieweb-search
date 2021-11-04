import requests
from config import ROOT_DIRECTORY

def run_test_queries():
    queries = ["coffee", "steampunk", "obadiah", "chemex", "aeropress recipe", "indieweb", "build a website", "cold brew", "PuckPuck", "speciality coffee", "accessibility", 'web category:"IndieWeb"', 'aeropress category:"Coffee" before:"2021-05-10"']

    with open(ROOT_DIRECTORY + "/data/test_queries.md", "w+") as f:
        for q in queries:
            r = requests.get('https://search.jamesg.blog/results?query="{}"&json=true'.format(q))

            to_show = ["{} - {}".format(item[0], item[2]) for item in r.json()]

            f.write("**First results page for '{}' query**\n\n".format(q))
            for item in to_show:
                f.write("- {}\n".format(item))