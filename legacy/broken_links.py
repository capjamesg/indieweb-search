import csv
import datetime

import pandas as pd
import requests

import config

date = datetime.datetime.now().strftime("%Y-%m-%d")


def check_for_invalid_links():
    # Read data/all_links.csv into a pandas dataframe
    df = pd.read_csv("data/all_links.csv", sep=",")

    df = df[df["link_type"] == "external"]

    external_links = df["link_to"].unique()

    # with open("data/all_links.csv", "r") as file:
    # 	external_links = csv.reader(file, delimiter=',')

    link_status = []

    links_tried = {}

    print(len(external_links))

    for link in external_links:
        print("trying {}".format(link))
        try:
            get_link = requests.head(link, headers=config.HEADERS, timeout=5)

            link_status.append(
                {
                    "url": link,
                    "status_code": get_link.status_code,
                    "domain_name": link.split("/")[2],
                }
            )

            links_tried[link] = True
        except:
            print("link error")

    with open(config.ROOT_DIRECTORY + "/data/invalid_external_links.csv", "w+") as file:
        writer = csv.writer(file)
        writer.writerow(["url", "status_code", "domain_name", "date"])
        for b in link_status:
            writer.writerow([b["url"], b["status_code"], b["domain_name"], date])


# check_for_invalid_links()
