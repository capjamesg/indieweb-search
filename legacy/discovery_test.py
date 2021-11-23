import mf2py
import crawler.post_type_discovery as post_type_discovery

items = mf2py.parse(url="https://aaronparecki.com/2021/11/10/16/")

h_entry = items["items"][0]

response = post_type_discovery.get_post_type(h_entry)

print(response)