import mf2py

def discover_author(h_card, h_entry, full_url, original_h_card):	
	# if rel=author, look for h-card on the rel=author link
	if h_entry.get("rels") and h_entry["rels"].get("author"):
		rel_author = h_entry['rels']['author']

		if rel_author:
			h_card_url = rel_author[0]

	if h_card_url:
		if h_card_url.startswith("//"):
			h_card_url = "http:" + h_card_url
		elif h_card_url.startswith("/"):
			h_card_url = full_url + h_card_url
		elif h_card_url.startswith("http"):
			h_card_url = h_card_url
		else:
			h_card_url = None
		
	if h_card_url != None:
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

	if h_card == [] or h_card == None:
		h_card = original_h_card

	return h_card