from bs4 import BeautifulSoup
import sqlite3

connection = sqlite3.connect("search.db")

# with connection:
#     cursor = connection.cursor()

#     # get all keywords
#     keywords = cursor.execute("SELECT keywords, page_content FROM posts;").fetchall()

#     kw_list = {}

#     words = []

#     for keyword in keywords:
#         soup = BeautifulSoup(keyword[1], "html.parser")
#         text = soup.get_text()
#         words.extend([t.replace("\n", "") for t in text.split(" ") if t.isalnum()])

#         for k in keyword[0].split(","):
#             if kw_list.get(k.strip()) == None:
#                 kw_list[k.strip()] = 1
#             else:
#                 kw_list[k.strip()] += 1

#     print(len(set(words)))

# print([(item, value) for item, value in kw_list.items() if value > 5])

# calculate ratio of words to headings

with connection:
    cursor = connection.cursor()

    # get all headings
    page_content = cursor.execute("SELECT page_content FROM posts LIMIT 1;").fetchone()

    # count headings
    soup = BeautifulSoup(page_content[0], "html.parser")
    number_of_headings = len(soup.find_all("h1")) + len(soup.find_all("h2"))

    # count words
    words = [t.replace("\n", "") for t in soup.get_text().split(" ") if t.isalnum()]

    # show ratio of words to headings
    # 172.4 words per heading
    # if ratio is less than 50, do not index h2s
    print(len(words) / number_of_headings)