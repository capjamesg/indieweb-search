from bs4 import BeautifulSoup
import functools
import datetime
import random
import mf2py
import nltk

@functools.lru_cache()
def search_for_h2_memo(soup, new_cleaned_value_for_direct_answer):
    return [f for f in soup.find_all(["h2"]) if new_cleaned_value_for_direct_answer in f.text.lower()]

@functools.lru_cache()
def search_for_strong_memo(soup, cleaned_value):
    return [f for f in soup.find_all(["strong"]) if any(x in f.text.lower() for x in cleaned_value.strip().split(" "))]

def generate_featured_snippet(cleaned_value, cursor, special_result, nlp, url=None):
    # Generate a featured snippet for the search result
    if url == None:
        return "", special_result

    print(cleaned_value)
    
    if "who is" in cleaned_value or ("." in cleaned_value and len(cleaned_value.split(".")[0]) > 3 and len(cleaned_value.split(".")[0]) > 1):
        url = url.replace("https://", "").replace("http://", "").split("/")[0]
        post = cursor.execute("SELECT title, page_content FROM posts WHERE url = ? OR url = ?;", ("https://" + url + "/", "http://" + url + "/",)).fetchone()
    else:
        post = cursor.execute("SELECT title, page_content FROM posts WHERE url = ?;", (url,)).fetchone()

    new_cleaned_value_for_direct_answer = " ".join([w for w in cleaned_value.split(" ") if w not in nltk.corpus.stopwords.words("english") + ["do", "you", "use"]]).split(" ")[0].strip()

    # get post with home brew bar url

    proper_nouns = [word.lower() for word, pos in nltk.tag.pos_tag(post[0].split()) if pos == 'NNP']

    # remove all proper nouns from cleaned_value

    original_cleaned_value = cleaned_value
    cleaned_value = " ".join([w for w in cleaned_value.split(" ") if "james" not in w.lower() and w.lower() not in proper_nouns and w.lower() not in post[0].replace("recipe", "").lower().split()])

    # read post with bs4
    soup = BeautifulSoup(post[1], "lxml")

    # remove stop words from question

    all_locations = []

    # if "what is" in original_cleaned_value
    if "what is" in original_cleaned_value:
        #  if "is a" in p.text.lower() or "are an" in p.text.lower() and original_cleaned_value.lower() in p.text.lower() 
        p_tags = [p for p in soup.find_all(["p", "span"]) if "p-summary" in p.attrs.get("class", [])]

        if len(p_tags) > 0:
            return "<p>{}</p>".format(p_tags[0]), {"type": "direct_answer", "breadcrumb": url, "title": soup.find("h1").text}

    if "who is" in original_cleaned_value or ("." in original_cleaned_value and len(original_cleaned_value.split(".")[0]) > 3 and len(original_cleaned_value.split(".")[0]) > 1):
        cleaned_value = " ".join([item for item in original_cleaned_value.split(" ") if item != "who" and item != "is"])

        mf2s = mf2py.parse(doc=soup)["items"]

        h_card = ""

        for item in mf2s:
            if item.get("type") and item.get("type")[0] == "h-card":
                h_card = item
                break

        if h_card == "":
            for item in mf2s:
                if item.get("type") and item.get("type")[0] == "h-entry":
                    h_card = item.get("properties").get("author")[0]
                    break

        if h_card == None:
            h_card = ""

        # if mf2py.parse(doc=soup)["items"][0].get("type") and "h-entry" in mf2py.parse(doc=soup)["items"][0].get("type") \
        #     and mf2py.parse(doc=soup)["items"][0]["properties"] and "author" in mf2py.parse(doc=soup)["items"][0]["properties"].get("author"):
        #     h_card = mf2py.parse(doc=soup)["items"][0]["properties"]

        # h_card = ""

        # print(h_card)
        # get bio from hcard
        to_show = ""

        print(h_card)

        if len(h_card) > 0:
            print('s')
            name = h_card["properties"].get("name")

            if name:
                name = h_card["properties"].get("name")[0]
            else:
                name = ""

            photo = h_card["properties"].get("photo")
            
            if photo:
                photo = h_card["properties"].get("photo")[0]
            else:
                photo = ""

            for key, value in h_card["properties"].items():
                if key != "photo":
                    to_show += "<p><b>{}</b>: {}</p>".format(key.title(), value[0])
            if soup.find("h1"):
                title = soup.find("h1").text
            else:
                title = url
            return "<img src='{}'><p>{}</p>".format(photo, to_show), {"type": "direct_answer", "breadcrumb": url, "title": title}
    
    if "founder" in cleaned_value or "owner" in cleaned_value:
        ent_type = "PERSON"
    elif "cafes" in cleaned_value or "location" in cleaned_value:
        ent_type = "GPE"
        all_locations = [w for w in nlp(" ".join(soup.get_text().replace("\n", ". ").split(". "))).ents if w.label_ == "GPE" and "in" in w.text]
        if len(all_locations) > 0:
            all_locations = all_locations[0]
    elif "opened" in cleaned_value or "established" in cleaned_value or "founded" in cleaned_value or "started" in cleaned_value:
        ent_type = "DATE"
    else:
        ent_type = "NONE"

    if ent_type != "NONE":
        sentence_with_query = [s for s in soup.get_text().replace("\n", ". ").split(". ") if all(x in s.lower() for x in original_cleaned_value.strip().split(" "))]

        if len(sentence_with_query) > 0:
            ents = [w for w in nlp(sentence_with_query[0]).ents if w.label_ == ent_type]

            if len(ents) > 0:
                return "<b style='font-size: 22px'>{}</b><br>{}".format(ents[0].text, sentence_with_query[0].replace("\n", " ")), {"type": "direct_answer", "breadcrumb": url, "title": soup.find("h1").text}
            elif len(all_locations) > 0:
                return "<b style='font-size: 22px'>{}</b><br>{}".format(all_locations[0].text, sentence_with_query[0]), {"type": "direct_answer", "breadcrumb": url, "title": soup.find("h1").text}
    
    # initialize tokenizer for later use with nltk
    t = nltk.tokenize.WhitespaceTokenizer()

    c = nltk.text.Text(t.tokenize(soup.text))

    if soup.find_all("dfn"):
        special_result = {"type": "direct_answer", "breadcrumb": url, "title": soup.find("h1").text}

        return soup.find_all("dfn")[0].text, special_result

    if len(cleaned_value) != 0 and len(cleaned_value.split(" ")) > 0:
        try:
            do_i_use = c.concordance_list(new_cleaned_value_for_direct_answer, width=50)

            all_locs = [f for f in soup.find_all(["li"]) if new_cleaned_value_for_direct_answer in f.text.lower()]

            if len(all_locs) < 3:
                return "", special_result

            if all_locs:
                location_of_tag = all_locs[0]
                position_in__parent_list = location_of_tag.find_parent().index(location_of_tag)
            elif len((soup, new_cleaned_value_for_direct_answer)) > 0:
                position_in__parent_list = 0
                all_locs = soup.find_all(["h2"])
                location_of_tag = all_locs[0]
            elif len(search_for_strong_memo(soup, cleaned_value)) > 0:
                all_locs = search_for_strong_memo(soup, cleaned_value)
                location_of_tag = all_locs[0]
            else:
                all_locs = [f for f in soup.find_all(["p"]) if cleaned_value in f.text.lower()]
                location_of_tag = all_locs[0]

            if location_of_tag.find_parent().name != "article" and location_of_tag.name == "li":
                # Show previous element for context and content addressing visitor query
                if position_in__parent_list - 2 < 0:
                    start = 0
                    add_ellipses = ""
                else:
                    start = position_in__parent_list - 2
                    add_ellipses = "<li>...</li>"

                all_lis = [str(i) for i in location_of_tag.find_parent().children if i.name == "li"]
                first_five_children = all_lis[start:position_in__parent_list+3]

                if len(all_lis) == 4:
                    do_i_use = str(location_of_tag.find_parent().find_previous()) + "<{}>".format(str(location_of_tag.find_parent().name)) + "".join(all_lis) + "</{}>".format(location_of_tag.find_parent().name) + "<p>...</p>"
                elif len(list(location_of_tag.find_parent().children)) > 5:
                    do_i_use = str(location_of_tag.find_parent().find_previous()) + "<{}>".format(str(location_of_tag.find_parent().name)) + add_ellipses + "".join(first_five_children) + "<li>...</li>" + "</{}>".format(location_of_tag.find_parent().name)
                else:
                    do_i_use = str(location_of_tag.find_parent().find_previous()) + "<{}>".format(str(location_of_tag.find_parent().name)) + "".join(first_five_children) + "</{}>".format(location_of_tag.find_parent().name)
            elif location_of_tag and (location_of_tag.name == "h2" or location_of_tag.name == "h3"):
                do_i_use = "<ul>" + "".join(["<li>{}</li>".format(h2.text) for h2 in list(all_locs)]) + "</ul>"
            elif location_of_tag.name == "strong":
                do_i_use = "<b>" + str(location_of_tag.text) + "</b>" + str(location_of_tag.find_next())
            elif location_of_tag.name == "p":
                sentence = [w.text for w in location_of_tag.split(". ") if cleaned_value in w.text][0]
                do_i_use = "<b>" + str(sentence) + "</b>"
            elif location_of_tag.find_parent().name != "article":
                do_i_use = str(location_of_tag.find_parent().find_previous()) + str(location_of_tag.find_parent())
            else:
                do_i_use = ""

            special_result = {"type": "direct_answer", "breadcrumb": url, "title": soup.find("h1").text}
        except:
            do_i_use = ""
    else:
        do_i_use = ""

    # Protect against direct answers that are too long
    if len(do_i_use) > 400:
        do_i_use = ""
        special_result = {}

    return do_i_use, special_result

def aeropress_recipe():
    # Rounding helper function for timing

    def myround(x, base=5):
        result = base * round(x/base)
        if result == 10:
            result = 0
        return result

    # Generate brewing variables

    dose = random.randint(12, 16)
    
    dose_is_point_five = random.choice([True, False])
    
    inverted = random.choice([True, False])

    # 1 in 7 chance I get a "really coarse" recipe with a coarse grind and a long brew time
    type_is_really_coarse = random.randint(1, 7)

    if type_is_really_coarse == 1:
        grind_size = random.randint(24, 30)
        time_in_seconds = random.randint(180, 300)
    else:
        grind_size = random.randint(18, 24)
        time_in_seconds = random.randint(45, 150)

    time_long = str(datetime.timedelta(seconds=time_in_seconds))
    time = time_long.split(":", 1)[1]

    last_time_int = time[-1]
    last_time_first_three = time[:-1]
    last_time_rounded = str(myround(int(last_time_int)))

    time = last_time_first_three + last_time_rounded

    filters = random.randint(1, 2)
    water = "250"

    stir_times = random.randint(0, 6)

    stirring_options = ["before putting the cap on", "before pluging", "both before putting the cap on and before plunging"]

    stirring = random.choice(stirring_options)

    return dose, grind_size, time, filters, water, stirring, stir_times, dose_is_point_five, inverted