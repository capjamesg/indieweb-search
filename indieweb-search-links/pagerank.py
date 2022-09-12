import csv

dampening_effect = 0.85

with open("links.csv", "r") as f:
    links = list(csv.reader(f))

graph = {}

def get_page_rank(incoming_domain, page_rank_guess, graph):
    page_rank = (1 - dampening_effect) + dampening_effect * (page_rank_guess) / 1

    graph[incoming_domain] = page_rank

    return graph

for source, target, _ in links:
    if target not in graph:
        graph[target] = 0

    graph = get_page_rank(target, graph.get(target, 0.15), graph)

    print("calculated PR for", target)


with open("page_rank.csv", "w") as f:
    writer = csv.writer(f)
    writer.writerows(graph.items())