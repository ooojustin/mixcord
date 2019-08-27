import requests
import re
import random
import html
import json

def get_raw_page(p = 1):
    url = f"https://onelinefun.com/puns/{p}/"
    response = requests.get(url)
    return response.text

PAGE_PATTERN = re.compile(r"Page \d+ of (\d+)")
JOKE_PATTERN  = re.compile(r"<div class=\"o\" itemscope itemtype=\"http://schema.org/CreativeWork\"><p>(.*?)</p>")

all_jokes = list()
page = get_raw_page()
match = PAGE_PATTERN.search(page)
max_page = int(match.group(1))
for page in range(max_page):
    page += 1
    print(f"scraping page {page}/{max_page}...")
    page = get_raw_page(page)
    jokes = JOKE_PATTERN.findall(page)
    jokes = [html.unescape(j) for j in jokes]
    all_jokes.extend(jokes)

print(f"got {len(all_jokes)} jokes in total")

file = open("jokes.txt", "w")
file.write(json.dumps(all_jokes, indent = 4))
file.close()
