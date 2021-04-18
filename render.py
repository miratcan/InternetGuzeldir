import csv
import urllib.request
from slugify import slugify
import datetime
from os.path import join
from os import makedirs
from jinja2 import Environment, FileSystemLoader, select_autoescape
from openpyxl import load_workbook

from tempfile import TemporaryFile, NamedTemporaryFile

# TODO: Read these as parameters from shell.
DOCUMENT_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSXBGnECx6IhFmmeTt6QKLvy3rOvtvmUVaHq_Ubo1mPzWaJu_AfykRrJlurwrd9Ade9S5t7N4Zo2Qpa/pubhtml"
DOCUMENT_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSXBGnECx6IhFmmeTt6QKLvy3rOvtvmUVaHq_Ubo1mPzWaJu_AfykRrJlurwrd9Ade9S5t7N4Zo2Qpa/pub?output=xlsx"

CATEGORY_SEPARATOR = ">"
LINKS = "Bağlantılar"
CATEGORIES = "Kategoriler"

env = Environment(
    loader=FileSystemLoader('templates/'),
    autoescape=select_autoescape(['html', 'xml']))

def get_lines(worksheet):
    """Returns worksheet as list of lists"""
    result = []
    for idx, row in enumerate(worksheet.rows):
        if idx == 0:
            continue
        result.append(list(map(lambda cell: cell.value, row)))
    return result


def category_str_to_breadcrumbs(category_string):
    """
    Converts category string to list.

    >>> category_str_to_breadcrumbs("A > B > C")
    ["a", "b", "c"]
    """
    return list(
        filter(
            lambda breadcrumb: bool(breadcrumb), [
                breadcrumb.strip() for breadcrumb in
                category_string.split(CATEGORY_SEPARATOR)
            ]
        )
    )


def category_str_to_url(category_string):
    """
    Converts category string to url.

    >>> category_str_to_url("A > B > C")
    /a/b/c/
    """
    category_breadcrumbs = category_str_to_breadcrumbs(category_string)
    return ('/'.join(map(slugify, category_breadcrumbs))) + '/'


def build_categorised_links(workbook):

    categories_info = {}
    for line in get_lines(workbook[CATEGORIES]):
        categories_info[line[0]] = {
            'title': line[1] if len(line) >= 2 else None,
            'desc': line[2] if len(line) >= 3 else None
        }

    categories = {"categories": {}}

    for line in get_lines(workbook[LINKS]):
        title, url, desc, category_str, kind, lang, source, create_time =\
            line
        category_items = category_str_to_breadcrumbs(category_str)
        parent = categories
        for level in range(len(category_items)):

            if "categories" not in parent:
                parent["categories"] = {}
            else:
                parent['categories'] = dict(sorted(parent['categories'].items()))

            category_title = category_items[level]

            if category_str in categories_info and \
                categories_info[category_str]['title'] is not None:
                category_seo_title = categories_info[category_str]['title']
            else:
                category_seo_title = category_title

            if category_str in categories_info and \
                categories_info[category_str]['desc'] is not None:
                category_seo_desc = categories_info[category_str]['desc']
            else:
                category_seo_desc = None

            if category_title not in parent["categories"]:
                category_url = ('/'.join(map(slugify, category_items))) + '/'
                parent["categories"][category_title] = {
                    "title": category_title,
                    "seo_title": category_seo_title,
                    "seo_desc": category_seo_desc,
                    "category_url": category_url,
                    "level": level
                }

            parent = parent["categories"][category_title]
    
        if "links" not in parent:
            parent['links'] = []

        link = {
            'title': title, 'url': url, 'desc': desc,
            'kind': kind, 'lang': lang, "create_time": create_time,
            'category_url': category_str_to_url(category_str),
            'filename': slugify(url) + '.html'
        }
        parent['links'].append(link)
    return categories


def get_latest_links(workbook):

    links = []
    for line in get_lines(workbook[LINKS]):
        title, url, desc, category_str, tayp, lang, source, create_time = line
        links.append({
            "title": title, "url": url, "desc": desc,
            "tayp": tayp, "lang": lang,
            "category_url": category_str_to_url(category_str),
            "category_level": len(category_str_to_breadcrumbs(category_str)),
            "filename": slugify(url) + '.html',
            "source": source, "create_time": create_time,
        })
    return sorted(links, key=lambda i: i['create_time'], reverse=True)


temp_file = NamedTemporaryFile(suffix='.xlsx')
temp_file.write(urllib.request.urlopen(DOCUMENT_URL).read())
workbook = load_workbook(filename=temp_file.name, read_only=True)
categories = build_categorised_links(workbook)
latest_links = get_latest_links(workbook)[:20]

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

