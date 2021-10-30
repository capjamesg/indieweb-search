import dns_cache
import requests
import cProfile

# dns_cache.override_system_resolver()

def make_requests():
    for i in range(10):
        requests.get("https://jamesg.blog")

cProfile.run("make_requests()", filename="profile.out")