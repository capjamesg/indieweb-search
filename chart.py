import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd
import sqlite3
from nltk import FreqDist
from networkx.drawing.nx_agraph import graphviz_layout

import spacy

nlp = spacy.load("en_core_web_md")

def plot_keyword_frequency():
    connection = sqlite3.connect("search.db")
    cursor = connection.cursor()

    keywords = cursor.execute("SELECT keywords FROM posts;").fetchall()

    all_keywords = []

    for k in keywords:
        for l in k[0].split(", "):
            all_keywords.append(l)

    distribution = FreqDist(all_keywords)

    print(distribution.most_common(20))

    distribution.plot(20)

def plot_linkrot_by_date():
    plt.figure()

    plt.title("Linkrot by date")

    plt.xlabel("Date")

    plt.ylabel("Number of URLs")

    pd.read_csv("data/external_link_status.csv").groupby(["status_code"]).count()["url"].plot(kind="line")

    pd.read_csv("data/external_link_status.csv").groupby(["status_code"]).count()["url"].plot(kind="line")

    # df = df[df["status_code"] == 200]

    # df.plot(kind="line", x="date", y="status_code")

    plt.show()

    plt.savefig("charts/linkrot_by_date.png")

def keyword_knowledge_graph():
    keywords = []

    G = nx.Graph()

    connection = sqlite3.connect("search.db")
    cursor = connection.cursor()
    rows = cursor.execute("SELECT keywords, url FROM posts;").fetchall()

    count = 0

    for r in rows:
        if count == 150:
            break
        post_keywords = []
        # for keyword in r[0].split(", "):
        #     # if "what is" in keyword:
        #     G.add_node(keyword)
        #     if len(post_keywords) > 0:
        #         G.add_edge(post_keywords[0], keyword)
        for keyword in r[0].split(", "):
            keyword = keyword.replace("the", "").replace("this", "")
            post_keywords.append(keyword)
            G.add_node(keyword)
            # if not keyword.islower():
            #     G.add_edge("proper noun", keyword)
        for k in post_keywords:
            G.add_edge(post_keywords[0], k)

        count += 1

    nx.draw(G, with_labels=True)

    plt.plot()

    plt.show()

    print([n for n in G.neighbors("coffee") if "coffee" in n.lower() and n.islower()][:7])
    # get coffee edge
    # for n in G.neighbors(to_check):
    #     print(n)
    #     print(nlp(n).similarity(nlp(to_check)))
    #     if nlp(n).similarity(nlp(to_check)):
    #         print(nlp(n).similarity(nlp(to_check)))

    #plt.show()

    return G

def show_error_codes():
    df = pd.read_csv("data/external_link_status.csv")

    plt.suptitle("Error codes returned by external links (n={})".format(len(df)))

    plt.xlabel("Error code")

    plt.ylabel("Number of URLs")

    df.groupby("status_code").count()["url"].plot(kind="bar")

    plt.show()

    plt.save("static/error_codes.png")

def get_internal_link_count():
    # Read out.csv into dataframe
    df = pd.read_csv("data/all_links.csv")

    print(df)

    # Remove all NaN values
    df = df.dropna()

    # Should be internal, change back later
    df = df[df["link_type"] == "external"]

    df = df[~df["link_to"].str.contains("jamesg.blog", na=False)]

    df = df[~df["link_to"].str.startswith("/", na=False)]

    df = df[~df["link_to"].str.startswith("#", na=False)]

    GA = nx.from_pandas_edgelist(df, source="page_linking", target="link_to")

    plt.title("jamesg.blog Link Graph (n={})".format(len(GA.nodes())))

    # nx.draw(GA, with_labels=True, node_color=["red" if node == "https://jamesg.blog" else "green" for node in GA.nodes()])

    # plt.plot()

    # plt.show()

    pr = nx.pagerank(GA)

    print(pr)

    # print(sorted(GA.degree, key=lambda x: x[1], reverse=True)[0:5])

def get_link_graph(type_of_graph, url):
    # Read out.csv into dataframe
    connection = sqlite3.connect("search.db")

    with connection:
        cursor = connection.cursor()

        rows = cursor.execute("SELECT url FROM posts;").fetchall()

    # df = pd.read_csv("data/all_links.csv")

    # # Remove all NaN values
    # df.dropna()

    # df = df[df["link_type"] == "internal"]

    # print(df)

    df = pd.DataFrame(rows)

    plt.title("jamesg.blog site architecture")

    GA = nx.DiGraph()

    in_namespace = {}

    unique_namespaces = set()

    max_depth = 0

    for x in rows:
        namespaces = x[0].replace("https://jamesg.blog", "").split("/")[:-1]
        if len(x[0].replace("https://jamesg.blog", "").split("/")) > max_depth:
            max_depth = len(x[0].replace("https://jamesg.blog", "").split("/"))

        for i in range(0, len(namespaces)):
            # Exclude last value in namespace if its parent is numeric
            if namespaces[i-1] and namespaces[i-1].isnumeric() and i == len(namespaces) - 1:
                continue

            unique_namespaces.add(namespaces[i])

            if namespaces[i] == "":
                continue

            if len(namespaces[i]) > 15:
                print(namespaces[i])
                continue

            if namespaces[i-1]:
                GA.add_edge(namespaces[i-1], "/" + namespaces[i-1] + "/" + namespaces[i])
            else:
                GA.add_edge("/", namespaces[i])
            if in_namespace.get(namespaces[i-1]):
                in_namespace[namespaces[i-1]] = in_namespace[namespaces[i-1]] + 1
            else:
                in_namespace[namespaces[i-1]] = 1

    print(in_namespace)

    all_layers = []

    for num in range(1, max_depth):
        layer = [item for item in GA.nodes if len(item.split("/")) == num]
        all_layers.append(layer)

    print(all_layers)

    # nx.nx_agraph.write_dot(GA,'test.dot')

    # Remove all NaN values
    df.dropna()

    # if type_of_graph == "incoming_links":
    #     # Get incoming links to a page
    #     df = df[df["link_to"].str.contains(url)]
    #     print(df)
    # else:
    #     # Get outgoing links
    #     df = df[df["page_linking"].str.contains(url, na=False)]

    # df = df[df["link_type"] == "internal"]

    # plt.title("Incoming links to {} on jamesg.blog".format(url))

    # GA = nx.from_pandas_edgelist(df, source="page_linking", target="link_to")

    # nx.draw_networkx(GA)

    # plt.plot()

    # plt.show()

    pos = graphviz_layout(GA, prog="dot")

    nx.draw(GA, pos, with_labels=True)

    plt.plot()

    plt.show()

    # print("Edges: (connections between URLs) " + str(len(GA.edges())))
    # print("Nodes (URLs): " + str(len(GA.nodes())))

    # plt.show()

    # figure = plt.gcf()

    # figure.set_size_inches(8, 6)

    # plt.savefig("graph.png")

def get_external_link_graph():
    # Read out.csv into dataframe
    df = pd.read_csv("data/all_links.csv")

    # Remove all NaN values
    df.dropna()

    df = df[df["link_type"] == "external"]

    plt.title("External links from jamesg.blog")

    GA = nx.from_pandas_edgelist(df, source="page_linking", target="link_to")

    nx.draw(GA, with_labels=True)

    plt.plot()

    print("Edges: (connections between URLs) " + str(len(GA.edges())))
    print("Nodes (URLs): " + str(len(GA.nodes())))

    plt.show()

    figure = plt.gcf()

    figure.set_size_inches(8, 6)

    plt.savefig("graph.png")

# show_error_codes()

get_link_graph("incoming_links", "https://jamesg.blog/2020/09/04/how-i-use-webmentions")

# get_external_link_graph()

# get_internal_link_count()

# plot_linkrot_by_date()

# keyword_knowledge_graph()

# plot_keyword_frequency()