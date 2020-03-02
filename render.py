from jinja2 import Environment, FileSystemLoader, select_autoescape
import json
env = Environment(loader=FileSystemLoader('templates/'), 
                  autoescape=select_autoescape(['html', 'xml']))

with open('sections.json', 'r') as file:
    sections = json.load(file)

home = env.get_template('home.html.jinja2')

with open('docs/index.html', 'w')as file:
    file.write(home.render(sections=sections))
