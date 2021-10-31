link = {"href": "https://j"}

supported_protocols = ["http", "https"]

if ("://" in link.get("href") and link.get("href").split("://")[0] not in supported_protocols) or (":" in link.get("href") \
    and (not link.get("href").startswith("/") and not link.get("href").startswith("//") and not link.get("href").startswith("#") \
     and not link.get("href").split(":")[0] in supported_protocols)):
    # url is wrong protocol, continue
    print("Unsupported protocol for discovered url: " + link.get("href") + ", not adding to index queue")