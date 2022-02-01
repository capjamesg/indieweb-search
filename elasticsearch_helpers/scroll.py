# Function from https://simplernerd.com/elasticsearch-scroll-python/
# All credit to them for the function
def scroll(es, index, body, scroll, size, **kw):
    page = es.search(index=index, body=body, scroll=scroll, size=size, **kw)
    scroll_id = page["_scroll_id"]
    hits = page["hits"]["hits"]
    while len(hits):
        yield hits
        page = es.scroll(scroll_id=scroll_id, scroll=scroll)
        scroll_id = page["_scroll_id"]
        hits = page["hits"]["hits"]
