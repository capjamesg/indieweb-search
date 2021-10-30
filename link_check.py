import json
import csv

# open next_crawl.txt
with open('next_crawl.txt', 'r') as f:
    next_crawl = f.readlines()

domains_as_dict = {d: "" for d in next_crawl}

valid = 0

# open links.csv
with open('links.csv', 'r') as csvfile:
    reader = csv.reader(csvfile)
    for row in reader:
        print(row[0])
        if domains_as_dict.get(row[0].split("/")[2].replace("www.", "")):
            valid += 1

print(valid)