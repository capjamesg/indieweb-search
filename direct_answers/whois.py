import mf2py

def parse_whois(original_cleaned_value, soup, url, original_url): 
    if "who is" in original_cleaned_value or (("." in original_cleaned_value and len(original_cleaned_value.split(".")[0]) > 3 and len(original_cleaned_value.split(".")[0]) > 1 and len(original_cleaned_value.split(" ")) == 1)):
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
                photo = "https://" + url + "/" + h_card["properties"].get("photo")[0]
            else:
                photo = ""

            for key, value in h_card["properties"].items():
                if key != "photo" and key != "email" and key != "logo" and key != "url" and key !="uid" and type(value[0]) == str:
                    to_show += "<p><b>{}</b>: {}</p>".format(key.title().replace("-", " "), value[0].strip("/"))
                elif key == "email":
                    to_show += "<p><b>{}</b>: <a href='{}'>{}</a></p>".format(key.title(), "mailto:{}".format(value[0].replace("mailto:", "")), value[0].replace("mailto:", ""))
                elif key == "url":
                    if value[0].strip() == "":
                        to_show  += "<p><b>{}</b>: <a href='{}'>{}</a></p>".format("URL", original_url, original_url)
                    else:
                        to_show += "<p><b>{}</b>: <a href='{}'>{}</a></p>".format("URL", value[0], value[0].strip("/"))

            if soup.find("h1"):
                title = soup.find("h1").text
            else:
                title = url
                
            print("<img src='{}' height='100' width='100' style='float: right;'><p>{}</p>".format(photo, to_show))
                
            return "<img src='{}' height='100' width='100' style='float: right;'><p>{}</p>".format(photo, to_show), {"type": "direct_answer", "breadcrumb": original_url, "title": title}

    return None, None

def parse_social(original_cleaned_value, soup, url, original_url):
    if original_cleaned_value.endswith("social"):
        # get all rel=me links
        rel_me_links = soup.find_all("a", {"rel": "me"})
        print(rel_me_links)

        if len(rel_me_links) > 0:
            to_show = ""

            for link in rel_me_links:
                if link.get("href"):
                    to_show += "<li><a href='{}'>{}</li>".format(link.get("href"), link.get("href"))

            if soup.find("h1"):
                title = soup.find("h1").text
            else:
                title = url

            return "<h3>{} Social Links</h3><ul>{}</ul>".format(title, to_show), {"type": "direct_answer", "breadcrumb": original_url, "title": title}

    return None, None

def parse_get_rel(original_cleaned_value, soup, url, original_url):
    # get all feeds on a page
    if original_cleaned_value.endswith("get rel"):
        # get all rel values
        rel_values = soup.select("link[rel]")

        to_show = ""

        for link in rel_values:
            to_show += "<li>{}: <a href='{}'>{}</li>".format("".join(link.get("rel")), link.get("href"), link.get("href"))

        return "<h3>'Rel' Attributes for {}</h3><ul>{}</ul>".format(original_url.replace("https://", "").replace("http://", "").strip("/"), to_show), {"type": "direct_answer", "breadcrumb": original_url, "title": soup.find_all("h1")[0].text}

    return None, None

def parse_feed(original_cleaned_value, soup, url, original_url):
    # get all feeds on a page
    if original_cleaned_value.endswith("inspect feed"):
        to_show = ""
        feeds = soup.find_all("link", {"rel": "alternate"})

        # check for h-feed
        h_feed = soup.select(".h-feed")

        if h_feed:
            to_show += "<li><b>Microformats h-feed</b>: <a href='{}'>{}</li>".format(url, url)

        if len(feeds) > 0:
            to_show = ""

            for link in feeds:
                if link.get("href"):
                    link_type = link.get("type")
                    if link_type:
                        link_type = link_type.split("/")[1].split("+")

                        if link_type != None:
                            link_type = link_type[0]

                            to_show += "<li><b>{} feed</b>: <a href='{}'>{}</a></li>".format(link_type, link.get("href"), link.get("href"))
                        elif link_type == "application/json":
                            link_type = "JSON"

                            to_show += "<li><b>{} feed</b>: <a href='{}'>{}</a></li>".format(link_type, link.get("href"), link.get("href"))
                    else:
                        to_show += "<li><b>Feed</b>: <a href='{}'>{}</a></li>".format(link.get("href"), link.get("href"), link.get("href"))

            if soup.find("h1"):
                title = soup.find("h1").text
            else:
                title = url

            return "<h3>{} Feeds</h3><ul>{}</ul>".format(title, to_show), {"type": "direct_answer", "breadcrumb": original_url, "title": title}

    return None, None