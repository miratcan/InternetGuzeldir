from jinja2 import Environment, FileSystemLoader, select_autoescape
import urllib.request
import csv
import codecs
from collections import defaultdict

URL = "https://docs.google.com/spreadsheets/u/3/d/" \
          "1mK5BycfvwvuPcekTKIMhPKtsRa0EXe-dGeQsvok5wz4/pub?output=csv"

env = Environment(
    loader=FileSystemLoader('templates/'),
    autoescape=select_autoescape(['html', 'xml']))

stream = urllib.request.urlopen(URL)
csv_file = csv.reader(codecs.iterdecode(stream, 'utf-8'))

next(csv_file)

sections = defaultdict(dict)

for line in csv_file:
    title, url, desc, category, tayp, lang = \
        line
    sections[category][title] = {
        'url': url,
        'desc': desc,
        'tayp': tayp,
        'lang': lang
    }


"""
with open('sections.json', 'r') as file:
    sections = json.load(file)
"""
home = env.get_template('home.html.jinja2')

with open('docs/index.html', 'w')as file:
    file.write(home.render(sections=sections))
