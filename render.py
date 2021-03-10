import csv
import urllib.request
from slugify import slugify
import datetime
from os.path import join
from os import makedirs
import pprint


CATEGORY_SEPARATOR = ">"

from jinja2 import Environment, FileSystemLoader, select_autoescape

env = Environment(
    loader=FileSystemLoader('templates/'),
    autoescape=select_autoescape(['html', 'xml']))


def category_str_to_items(cstr):
    return list(filter(lambda i: bool(i),
        [i.strip() for i in cstr.split(CATEGORY_SEPARATOR)]
    ))

def category_str_to_url(cstr):
    category_items = category_str_to_items(cstr)
    return ('/'.join(map(slugify, category_items))) + '/'


def get_categories(csv_lines):
    csv_reader = csv.reader(csv_lines)

    categories = {"categories": {}}

    for line in csv_reader:
        title, url, desc, category_str, tayp, lang, source = line[:-1]
        category_items = category_str_to_items(category_str)
        parent = categories
        for level in range(len(category_items)):
            if "categories" not in parent:
                parent["categories"] = {}
            else:
                parent['categories'] = dict(sorted(parent['categories'].items()))
            category_title = category_items[level]

            if category_title not in parent["categories"]:
                category_url = ('/'.join(map(slugify, category_items))) + '/'
                parent["categories"][category_title] = {
                    "title": category_title,
                    "category_url": category_url,
                    "level": level
                }

            parent = parent["categories"][category_title]
    
        if "links" not in parent:
            parent['links'] = []

        link = {
            'title': title, 'url': url, 'desc': desc,
            'tayp': tayp, 'lang': lang,
            'category_url': category_str_to_url(category_str),
            'filename': slugify(url) + '.html'
        }
        print(link)
        parent['links'].append(link)

    
    return categories


def get_latest_links(csv_lines):
    csv_reader = csv.reader(csv_lines)
    links = []
    for line in csv_reader:
        title, url, desc, category_str, tayp, lang, source, date_str = line
        date = datetime.datetime.strptime(date_str, "%d.%m.%Y").date()
        links.append({
            "title": title, "url": url, "desc": desc,
            "tayp": tayp, "lang": lang,
            "category_url": category_str_to_url(category_str),
            "category_level": len(category_str_to_items(category_str)),
            "filename": slugify(url) + '.html',
            "source": source, "date": date,

        })
    return sorted(links, key=lambda i: i['date'])



URL = "https://docs.google.com/spreadsheets/u/3/d/" \
      "1mK5BycfvwvuPcekTKIMhPKtsRa0EXe-dGeQsvok5wz4/pub?output=csv"

csv_lines = [
    l.decode("utf-8") for l in urllib.request.urlopen(URL).readlines()[1:]
]

categories = get_categories(csv_lines)
latest_links = get_latest_links(csv_lines)

home_template = env.get_template('home.html.jinja2')
link_template = env.get_template('link.html.jinja2')
category_template = env.get_template('category.html.jinja2')


def render_categories(sub_categories, level=0):
    for key, category in sub_categories.items():
        path = join('docs', category['category_url'])
        try:
            makedirs(path)
        except FileExistsError:
            pass
        with open(join(path, 'index.html'), 'w') as file:
            file.write(
                category_template.render(
                    current_category=category,
                    categories=categories
                )
            )
        if 'links' in category:
            for link in category['links']:
                with open(join(path, slugify(link['url'])) + '.html', 'w') as file:
                    file.write(link_template.render(
                        link=link, current_category=category, categories=categories))

        if 'categories' in category:
            render_categories(category['categories'], level=level+1)


render_categories(categories["categories"])
with open('docs/index.html', 'w')as file:
    file.write(home_template.render(categories=categories, latest_links=latest_links))

