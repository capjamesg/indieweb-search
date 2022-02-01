import csv
import datetime

import matplotlib.pyplot as plt
import pandas as pd
from elasticsearch import Elasticsearch

from config import ROOT_DIRECTORY

es = Elasticsearch(["http://localhost:9200"])

total_docs_today = int(es.count(index="pages")["count"])

today = datetime.datetime.now().strftime("%Y-%m-%d")

# read domains.txt
with open(ROOT_DIRECTORY + "/domains.txt", "r") as domains_file:
    domains = domains_file.readlines()

domain_count = len(domains)

with open("stats.csv", "a") as stats_file:
    writer = csv.writer(stats_file)
    writer.writerow([total_docs_today, today, domain_count])


def calculate_index_size():
    df = pd.read_csv(ROOT_DIRECTORY + "/stats.csv")

    fig, ax = plt.subplots()

    ax.ticklabel_format(useOffset=False)

    plt.subplots_adjust(bottom=0.2)

    plt.figure(num=1, figsize=(16, 12))

    plt.title("Number of web pages indexed")

    plt.xlabel("Date")

    plt.xticks(rotation=45)

    plt.ylabel("Total resources indexed")

    # get last 30 records
    df = df.tail(30)

    # df["end_time"] = pd.to_datetime(df["end_time"]).dt.date

    # df = df.groupby(["end_time"]).mean()["total_posts_indexed"]

    plt.plot(df["date"], df["total_posts_indexed"], label="Total Posts Indexed")

    plt.legend()

    plt.savefig(ROOT_DIRECTORY + "/static/index_size.png")


def calculate_domains_indexed():
    df = pd.read_csv(ROOT_DIRECTORY + "/stats.csv")

    fig, ax = plt.subplots()

    ax.ticklabel_format(useOffset=False)

    plt.subplots_adjust(bottom=0.2)

    plt.figure(num=2, figsize=(16, 12))

    plt.title("Number of domains from which content is indexed")

    plt.xlabel("Date")

    plt.xticks(rotation=45)

    plt.ylabel("Total resources indexed")

    # get last 30 records
    df = df.tail(30)

    plt.plot(df["date"], df["total_domains_indexed"], label="Total Domains Indexed")

    plt.legend()

    plt.savefig(ROOT_DIRECTORY + "/static/domain_index_size.png")


calculate_index_size()

calculate_domains_indexed()
