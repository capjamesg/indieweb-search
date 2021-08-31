import matplotlib.pyplot as plt
import pandas as pd
import sqlite3
from nltk import FreqDist
from config import ROOT_DIRECTORY

def calculate_index_size():
    df = pd.read_csv(ROOT_DIRECTORY + "/data/index_stats.csv")
    	
    df.columns = ["total_posts_indexed", "total_images_indexed", "pages_indexed", "images_indexed", "content_length", "start_time", "end_time", "duration", "external_link_count"]

    plt.figure(num=1)

    plt.title("Number of resources indexed (jamesg.blog)")

    plt.xlabel("Date")

    plt.xticks(rotation=45)

    plt.ylabel("Total resources indexed")

    df = df.tail(10)

    # df["end_time"] = pd.to_datetime(df["end_time"]).dt.date

    # df = df.groupby(["end_time"]).mean()["total_posts_indexed"]

    plt.plot(df["end_time"], df["total_posts_indexed"], label="Total Posts Indexed")

    plt.plot(df["end_time"], df["total_images_indexed"], label="Total Images Indexed")

    plt.legend()

    plt.savefig(ROOT_DIRECTORY + "/static/index_size.png")

def plot_keyword_frequency():
    connection = sqlite3.connect(ROOT_DIRECTORY + "/search.db")
    cursor = connection.cursor()

    keywords = cursor.execute("SELECT keywords FROM posts;").fetchall()

    all_keywords = []

    for k in keywords:
        for l in k[0].split(", "):
            all_keywords.append(l)

    fig = plt.figure()

    plt.title("Keywords that appear most frequently in the index")

    distribution = FreqDist(all_keywords)

    plt.plot(distribution.most_common(20))

    fig.savefig(ROOT_DIRECTORY + "/static/keyword_distribution.png")

def plot_linkrot_by_date():
    plt.figure(num=2)

    df = pd.read_csv(ROOT_DIRECTORY + "/data/external_link_status.csv")

    plt.title("Linkrot by date (jamesg.blog, n={})".format(len(df)))

    plt.xlabel("Date")

    plt.ylabel("Number of URLs")

    status_codes = df["status_code"].unique()

    # Group information by date and status code, count number of URLs on each date by status code
    # Reset index lets me create a column called "count" that I can use later
    df = df.groupby(["date", "status_code"])["url"].count().reset_index(name='count')

    # For each status code, make a line on the chart with the count of URLs on each date that returned that status code
    for s in status_codes:
        df_s = df[df["status_code"] == s]
        plt.plot(df_s["date"], df_s["count"], label=s)

    plt.legend()

    plt.savefig(ROOT_DIRECTORY + "/static/linkrot_by_date.png")

def show_error_codes():
    plt.figure(num=3)

    df = pd.read_csv(ROOT_DIRECTORY + "/data/external_link_status.csv")

    plt.suptitle("Error codes returned by external links (n={})".format(len(df)))

    plt.xlabel("Error code")

    plt.ylabel("Number of URLs")

    df.groupby("status_code").count()["url"].plot(kind="bar")

    plt.savefig(ROOT_DIRECTORY + "/static/error_codes.png")