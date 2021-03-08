import csv
import urllib.request
from slugify import slugify
import datetime


DEFAULT_CATEGORY_SEPARATOR = ">"

from jinja2 import Environment, FileSystemLoader, select_autoescape

env = Environment(
    loader=FileSystemLoader('templates/'),
    autoescape=select_autoescape(['html', 'xml']))


def get_from_parts(_dict, parts):
    elem = _dict
    for part in parts:
        try:
            elem = elem[part]
        except (KeyError, TypeError):
            return None
    return elem


def get_from_path(_dict, path, separator):
    parts = [part.strip() for part in path.split(separator)]
    return get_from_parts(_dict, parts)


def get_sections(csv_lines, category_separator=DEFAULT_CATEGORY_SEPARATOR):
    csv_reader = csv.reader(csv_lines)

    sections = {"links": [], "sections": {}, "title": "root", "path": "/"}

    for line in csv_reader:
        title, url, desc, category_str, tayp, lang, source = line[:-1]
        category_path = [part.strip() for part in category_str.split(
                         category_separator)]
        category_path = list(filter(lambda i: bool(i), category_path))
        parent = sections
        for level in range(len(category_path)):
            if "sections" not in parent:
                parent["sections"] = {}
            else:
                parent['sections'] = dict(sorted(parent['sections'].items()))
            section_title = category_path[level]

            if section_title not in parent["sections"]:
                category_slug = slugify(category_str, separator='-',
                        replacements=[['>', '_'],])

                parent["sections"][section_title] = {
                    "title": section_title,
                    "category_str": category_str,
                    "slug": category_slug
                }

            parent = parent["sections"][section_title]
    
        if "links" not in parent:
            parent['links'] = []
        parent['links'].append({'title': title, 'url': url, 'desc': desc,
                                'tayp': tayp, 'lang': lang})
    
    return sections


def get_latest_links(csv_lines):
    csv_reader = csv.reader(csv_lines)
    links = []
    for line in csv_reader:
        title, url, desc, category_str, tayp, lang, source, date_str = line
        date = datetime.datetime.strptime(date_str, "%d.%m.%Y").date()
        links.append({"title": title, "url": url, "desc": desc,
                      "category": category_str, "tayp": tayp, "lang": lang,
                      "source": source, "date": date})
    return sorted(links, key=lambda i: i['date'])



URL = "https://docs.google.com/spreadsheets/u/3/d/" \
      "1mK5BycfvwvuPcekTKIMhPKtsRa0EXe-dGeQsvok5wz4/pub?output=csv"

# URL = "https://docs.google.com/spreadsheets/d
# /1hE29WWJQ_sFnelcfWms7gHm8PnpLh4bVY6mdSP1S8SM/export?format=csv"

csv_lines = [
    l.decode("utf-8") for l in urllib.request.urlopen(URL).readlines()[1:]
]

sections = get_sections(csv_lines, category_separator=">")
import json
print(json.dumps(sections))

latest_links = get_latest_links(csv_lines)
home = env.get_template('home.html.jinja2')

with open('docs/index.html', 'w')as file:
    file.write(home.render(sections=sections, latest_links=latest_links))