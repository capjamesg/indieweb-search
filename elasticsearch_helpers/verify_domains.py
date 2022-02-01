import requests

# make sure all domains in domains.txt are valid
# with open('domains.txt', 'r') as f:
#     to_check = f.read().splitlines()

# valid = []
# redirects = []

# for domain in to_check:
#     try:
#         r = requests.get('https://' + domain, timeout=4)
#     except:
#         print("skipping " + domain + " because the URL is invalid")
#         continue

#     if r.status_code == 200:
#         print("verified " + domain)
#         valid.append(domain)
#     elif r.status_code == 301 or r.status_code == 302 or r.status_code == 303 or r.status_code == 307 or r.status_code == 308:
#         print(domain + ' redirects to ' + r.headers['Location'])
#         redirects.append(r.headers['Location'])
#     else:
#         print("skipping " + domain + " because the URL is invalid")

# # write valid to file
# with open('valid_domains.txt', 'w') as f:
#     for v in valid:
#         f.write(v + '\n')

# with open('redirects.txt', 'w') as f:
#     for r in redirects:
#         f.write(r + '\n')

with open("valid_domains.txt", "r") as f:
    domains = f.read().splitlines()

unique_domains = []

for domain in domains:
    if domain.startswith("www.") and domain.replace("www.", "") in domains:
        unique_domains.append(domain.replace("www.", ""))
    else:
        unique_domains.append(domain)

print(unique_domains)

with open("final_valid_domains.txt", "w+") as f:
    for domain in unique_domains:
        f.write(domain + "\n")
