def parse_review(original_cleaned_value, soup, url, post):
    if "review" in original_cleaned_value:
        h_review = soup.select(".h-review")

        if h_review:
            h_review = h_review[0]
            
            name = h_review.select(".p-name")[0].text

            if not name:
                name = soup.find("title")

            rating = h_review.select(".p-rating")

            if not rating:
                rating = h_review.select(".rating")[0].text

            if not rating:
                rating = ""

            review = h_review.select(".e-content")

            if review:
                # only show first four sentences of review
                review = ". ".join(review[0].text.split(". ")[:4]) + "..."
            else:
                review = ""

            return "<h3>Review of {}</h3><p>Rating: {}</p><p>{}</p>".format(name, rating, review), {"type": "direct_answer", "breadcrumb": url, "title": post["title"]}

    return None, None