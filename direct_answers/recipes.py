def parse_recipe(original_cleaned_value, soup, url, post):
    if "recipe" in original_cleaned_value:
        h_recipe = soup.select(".h-recipe")

        if h_recipe:
            h_recipe = h_recipe[0]

            name = h_recipe.select(".p-name")

            if not name:
                name = soup.find("title")

            ingredients = [
                "<li>" + x.text + "</li>" for x in h_recipe.select(".p-ingredient")
            ]

            instructions = h_recipe.select(".e-instructions")[0].find_all("li")

            instructions = ["<li>" + x.text + "</li>" for x in instructions]

            if len(ingredients) > 0 and len(instructions) > 0:
                return "<h3>Ingredients</h3><p>{}</p><h3>Instructions</h3><p>{}</p>".format(
                    "".join(i for i in ingredients), "".join(i for i in instructions)
                ), {
                    "type": "direct_answer",
                    "breadcrumb": url,
                    "title": post["title"],
                }

    return None, None
