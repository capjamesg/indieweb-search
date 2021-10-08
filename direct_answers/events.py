import datetime
from .whereis import parse_geo

def parse_event(original_cleaned_value, soup, url, post):
    if "event" in original_cleaned_value or soup.select(".h-event"):
        h_event = soup.select(".h-event")

        h_feed = soup.select(".h-feed")
        
        if len(h_event) > 0 and not h_feed:
            h_event = h_event[0]

            name = h_event.select(".p-name")

            if name:
                name = name[0].text
            else:
                name = soup.find("title")

            start_date = h_event.select(".dt-start")

            try:
                if start_date:
                    start_date = start_date[0].get("value")
                    start_date = datetime.datetime.strptime(start_date, "%Y-%m-%dT%H:%M:%S%z").strftime("%B %d, %Y (%H:%M)")
                else:
                    start_date = ""

                end_date = h_event.select(".dt-end")

                if end_date:
                    end_date = end_date[0].get("value")
                    end_date = datetime.datetime.strptime(end_date, "%Y-%m-%dT%H:%M:%S%z").strftime("%B %d, %Y (%H:%M)")
                else:
                    end_date = ""
            except:
                start_date = ""
                end_date = ""

            location = h_event.select(".location")

            if location:
                location = location[0].text
            else:
                location = ""

            summary = h_event.select(".p-summary")

            if summary:
                summary = summary[0].text
            else:
                summary = ""

            if summary == "":
                summary = h_event.select(".e-content")
            
            if summary and len(summary) > 0:
                summary = ". ".join(summary[0].text.split(".")[:2]) + "..."

            add_image = parse_geo(soup)

            if add_image != None:
                return "<h3>{}</h3>{}<p><b>Event start:</b> {}</p><p><b>Event end:</b> {}</p><p><b>Location:</b> {}</p><p>{}</p>".format(name, add_image, start_date, end_date, location, summary), {"type": "direct_answer", "breadcrumb": url, "title": post["title"]} 
            else:
                return "<h3>{}</h3><p><b>Event start:</b> {}</p><p><b>Event end:</b> {}</p><p><b>Location:</b> {}</p><p>{}</p>".format(name, start_date, end_date, location, summary), {"type": "direct_answer", "breadcrumb": url, "title": post["title"]} 

    return None, None