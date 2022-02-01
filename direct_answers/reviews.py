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

            return "<h3>Review of {}</h3><p>Rating: {}</p><p>{}</p>".format(
                name, rating, review
            ), {"type": "direct_answer", "breadcrumb": url, "title": post["title"]}

    return None, None


def parse_aggregate_review(original_cleaned_value, soup, url, post):
    if "aggregate review" in original_cleaned_value:
        h_review = soup.select(".h-review-aggregate")

        if h_review:
            h_review = h_review[0]

            to_show = ""

            if not h_review.select(".p-item"):
                return None, None

            to_show += "<p>" + h_review.select(".p-item")[0].text + "</p>"

            supported_properties = [
                "p-average",
                "p-best",
                "p-worst",
                "p-count",
                "p-votes",
            ]

            for property in supported_properties:
                if h_review.select(".{}".format(property)):
                    to_show += "<li><b>{}</b>{}</li>".format(
                        property.replace("p-", "").title(),
                        h_review.select(".{}".format(property))[0].text,
                    )

            return "<h3>Aggregate review of {}</h3><ul>{}</ul>".format(to_show), {
                "type": "direct_answer",
                "breadcrumb": url,
                "title": post["title"],
            }

    return None, None
