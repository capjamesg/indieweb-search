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

def generate_featured_snippet(cleaned_value, special_result, nlp, url=None, post=None, direct=False):
    # Generate a featured snippet for the search result
    if url == None:
        return "", special_result

    original_url = url
    
    if "who is" in cleaned_value:
        url = url.replace("https://", "").replace("http://", "").split("/")[0]

    new_cleaned_value_for_direct_answer = " ".join([w for w in cleaned_value.split(" ") if w not in nltk.corpus.stopwords.words("english") or w in ["why", "how"]]).split(" ")[0].strip()

    # get post with home brew bar url

    proper_nouns = [word.lower() for word, pos in nltk.tag.pos_tag(post["title"].split()) if pos == 'NNP']

    # remove all proper nouns from cleaned_value

    original_cleaned_value = cleaned_value.lower()
    cleaned_value = " ".join([w for w in cleaned_value.split(" ") if "james" not in w.lower() and w.lower() not in proper_nouns and w.lower() not in post["title"].lower().split() and w.lower() not in post["url"].lower().split("/")[-1]])

    # read post with bs4
    soup = BeautifulSoup(post["page_content"], "lxml")

    # remove stop words from question

    all_locations = []

    # if "what is" in original_cleaned_value
    if "what is" in original_cleaned_value or "what are" in original_cleaned_value or direct == True or "microformats" in original_cleaned_value:
        #  if "is a" in p.text.lower() or "are an" in p.text.lower() and original_cleaned_value.lower() in p.text.lower() 
        original_cleaned_value = original_cleaned_value.replace("what is", "").replace("what are", "").strip().lower()

        p_tags = [p.text for p in soup.find_all(["p", "span"]) if ("p-summary" in p.attrs.get("class", []) and p.text != None) or "{} is".format(original_cleaned_value) in p.text.lower() or "{} are".format(original_cleaned_value) in p.text.lower()]

        if soup.find("h1"):
            title = soup.find("h1").text
        elif soup.find("title"):
            title = soup.find("title").text
        else:
            title = "IndieWeb"

        if len(p_tags) > 0:
            return "<p>{}</p>".format(p_tags[0]), {"type": "direct_answer", "breadcrumb": url, "title": title}

    if "who is" in original_cleaned_value or (("." in original_cleaned_value and len(original_cleaned_value.split(".")[0]) > 3 and len(original_cleaned_value.split(".")[0]) > 1 and len(original_cleaned_value.split(" ")) == 1)):
        cleaned_value = " ".join([item for item in original_cleaned_value.split(" ") if item != "who" and item != "is"])

        mf2s = mf2py.parse(doc=soup)["items"]

        h_card = ""

        for item in mf2s:
            if item.get("type") and item.get("type")[0] == "h-card":
                h_card = item
                break

        if h_card == "":
            for item in mf2s:
                if item.get("type") and item.get("type")[0] == "h-entry" and item.get("properties") and item.get("properties").get("author"):
                    h_card = item.get("properties").get("author")[0]
                    break

        if h_card == None:
            h_card = ""

        to_show = ""

        if len(h_card) > 0:
            name = h_card["properties"].get("name")

            if name:
                name = h_card["properties"].get("name")[0]
            else:
                name = ""

            photo = h_card["properties"].get("photo")
            
            if photo and photo[0].startswith("/"):
                photo = "https://" + url + h_card["properties"].get("photo")[0]
            elif photo and photo[0].startswith("http"):
                photo = photo[0]
            elif photo and photo[0].startswith("//"):
                photo = "https:" + photo[0]
            elif photo:
                photo = photo
            else:
                photo = ""

            for key, value in h_card["properties"].items():
                if key != "photo":
                    to_show += "<p><b>{}</b>: {}</p>".format(key.title(), value[0])
            if soup.find("h1"):
                title = soup.find("h1").text
            else:
                title = url
            return "<img src='{}'><p>{}</p>".format(photo, to_show), {"type": "direct_answer", "breadcrumb": original_url, "title": title}
    
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
        sentence_with_query = [s for s in soup.get_text().replace("\n", ". ").split(". ") if all(x in s.lower() for x in cleaned_value.strip().split(" "))]

        if len(sentence_with_query) > 0:
            ents = [w for w in nlp(sentence_with_query[0]).ents if w.label_ == ent_type]

            if len(ents) > 0:
                return "<b style='font-size: 22px'>{}</b><br>{}".format(ents[0].text, sentence_with_query[0].replace("\n", " ")), {"type": "direct_answer", "breadcrumb": url, "title": soup.find("h1").text}
            elif len(all_locations) > 0:
                return "<b style='font-size: 22px'>{}</b><br>{}".format(all_locations[0].text, sentence_with_query[0]), {"type": "direct_answer", "breadcrumb": url, "title": soup.find("h1").text}
    
    # initialize tokenizer for later use with nltk
    t = nltk.tokenize.WhitespaceTokenizer()

    c = nltk.text.Text(t.tokenize(soup.text))

    # if soup.find_all("dfn"):
    #     special_result = {"type": "direct_answer", "breadcrumb": url, "title": soup.find("h1").text}

    #     return soup.find_all("dfn")[0].text, special_result

    if len(cleaned_value) != 0 and len(cleaned_value.split(" ")) > 0:
        try:
            do_i_use = c.concordance_list(new_cleaned_value_for_direct_answer, width=50)

            all_locs = [f for f in soup.find_all(["li"]) if new_cleaned_value_for_direct_answer in f.text.lower()]

            # if len(all_locs) < 3:
            #     return "", special_result

            # check if in h2
            in_h2 = [f for f in soup.find_all(["h2"]) if new_cleaned_value_for_direct_answer in f.text.lower()]

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
            print(len(in_h2))
            if len(in_h2) == 1:
                print('x')
                # get p after in_h2
                location_of_tag = in_h2[0]

                location_of_tag = "<br>".join([f.text for f in location_of_tag.find_next_siblings()][:3])

                return "<b>{}</b><br>{}".format(in_h2[0].text, location_of_tag), {"type": "direct_answer", "breadcrumb": url, "title": soup.find("h1").text}

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

            if len(BeautifulSoup(do_i_use, "lxml").get_text()) < 60:
                return "", special_result

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