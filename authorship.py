import mf2py

h_card = []
h_card_url = None

h_entry = mf2py.parse(url="https://authorship.rocks/test/5/")

for i in h_entry["items"]:
    if i['type'] == ['h-entry']:
        if i['properties'].get('author'):
            # if author is h_card
            if type(i['properties']['author'][0]) == dict and i['properties']['author'][0].get('type') == ['h-card']:
                h_card = i['properties']['author'][0]
                break

            elif type(i['properties']['author']) == list:
                h_card = i['properties']['author'][0]
                break
            
# if rel=author
if h_card == []:
    # get rel=author from h_entry
    rel_author = h_entry['rels']['author']

    if rel_author:
        h_card_url = rel_author[0]

if h_card_url:
    new_h_card = mf2py.parse(url=h_card_url)

    if new_h_card.get("rels") and new_h_card.get("rels").get("me"):
        rel_mes = new_h_card['rels']['me']
    else:
        rel_mes = []

    for j in new_h_card["items"]:
        if j.get('type') and j.get('type') == ['h-card'] and j['properties']['url'] == rel_author and j['properties'].get('uid') == j['properties']['url']:
            h_card = j
            break
        elif j.get('type') and j.get('type') == ['h-card'] and j['properties'].get('url') in rel_mes:
            h_card = j
            break
        elif j.get('type') and j.get('type') == ['h-card'] and j['properties']['url'] == rel_author:
            h_card = j
            break

print(h_card)