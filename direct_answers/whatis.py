def parse_what_is(original_cleaned_value, soup, url, direct): 
    # if "what is" in original_cleaned_value
    if "what is" in original_cleaned_value or "what are" in original_cleaned_value or "what were" in original_cleaned_value or direct == True or "microformats" in original_cleaned_value:
        #  if "is a" in p.text.lower() or "are an" in p.text.lower() and original_cleaned_value.lower() in p.text.lower() 
        original_cleaned_value = original_cleaned_value.replace("what is", "").replace("what are", "").replace("what were", "").strip().lower()

        p_tags = [p.text for p in soup.find_all(["p", "span"]) if ("p-summary" in p.attrs.get("class", []) and p.text != None) or "{} is".format(original_cleaned_value) in p.text.lower() or "{} are".format(original_cleaned_value) in p.text.lower()]

        if soup.find("h1"):
            title = soup.find("h1").text
        elif soup.find("title"):
            title = soup.find("title").text
        else:
            title = "IndieWeb"

        if len(p_tags) > 0:
            return "<p>{}</p>".format(p_tags[0]), {"type": "direct_answer", "breadcrumb": url, "title": title}
        
    return None, None