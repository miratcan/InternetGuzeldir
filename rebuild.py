import datetime
import urllib.request

from slugify import slugify
from os.path import join, exists, dirname, realpath
from os import makedirs as _makedirs
from collections import defaultdict
from jinja2 import Environment, FileSystemLoader, select_autoescape
from openpyxl import load_workbook
from tempfile import NamedTemporaryFile
from selenium import webdriver

DOCUMENT_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSXBGnECx6IhFmmeTt6QKLvy3rOvtvmUVaHq_Ubo1mPzWaJu_AfykRrJlurwrd9Ade9S5t7N4Zo2Qpa/pub?output=xlsx"


SITE_TITLE = "LINK SITE"
SITE_DESCRIPTION = "LINK SITE DESCRIPTION"

SEPERATOR = ">"

WORKBOOK_LINKS_TITLE = "Bağlantılar"
WORKBOOK_CATEGORIES_TITLE = "Kategoriler"

CATEGORY_COL = 3

LINK_COLUMNS = (
    "title",
    "url",
    "desc",
    "category_str",
    "kind",
    "lang",
    "source",
    "create_time",
)

env = Environment(
    loader=FileSystemLoader("templates/"),
    autoescape=select_autoescape(["html", "xml"]),
)


def get_lines(worksheet):
    result = []
    for idx, row in enumerate(worksheet.rows):
        if idx == 0:
            continue
        result.append(list(map(lambda cell: cell.value, row)))
    return result


def get_category_parts(id_):
    return list(
        filter(
            lambda part: bool(part),
            [part.strip() for part in id_.split(SEPERATOR)],
        )
    )


def get_category_path(id_):
    parts = get_category_parts(id_)
    return ("/".join(map(slugify, parts))) + "/"


def get_category_root_path(id_):
    return "../" * (get_category_depth(id_) + 1)


def get_category_depth(id_):
    return id_.count(SEPERATOR)


def get_category_parent_id(id_):
    if id_ is None:
        return None
    parts = get_category_parts(id_)
    return f" {SEPERATOR} ".join(parts[:-1]) if len(parts) > 1 else None


def get_link_from_line(line):
    link = {column: line[index] for index, column in enumerate(LINK_COLUMNS)}
    link["file_path"] = (
        get_category_path(line[CATEGORY_COL]) + slugify(link["url"]) + ".html"
    )
    return link


def get_links_by_category(lines):
    result = defaultdict(list)
    for line in lines:
        id_ = line[CATEGORY_COL]
        link = get_link_from_line(line)
        result[id_].append(link)
    return result


def create_category_paths(base_path, lines):
    ids = get_links_by_category(lines).keys()
    for id_ in ids:
        path = join(base_path, get_category_path(id_))
        makedirs(path)


def get_category_overrides(lines):
    overrides = {}
    for line in lines:
        override = {}
        if len(line) > 1 and line[1] is not None:
            override["title"] = line[1]
        if len(line) > 2 and line[2] is not None:
            override["desc"] = line[2]
        overrides[line[0]] = override
    return overrides


def get_category_info(id_, overrides):
    name = get_category_parts(id_)[-1]
    result = {
        "name": name,
        "title": name,
        "desc": None,
        "parent": None,
        "path": get_category_path(id_),
        "children": [],
    }
    result.update(overrides.get(id_, {}))
    return result


def get_max_category_depth(links_page_lines):
    max_depth = 0
    for line in links_page_lines:
        depth = get_category_depth(line[CATEGORY_COL])
        max_depth = max(max_depth, depth)
    return max_depth


def get_categories(links_page_lines, categories_page_lines):
    categories = {}
    overrides = get_category_overrides(categories_page_lines)
    for line in links_page_lines:
        id_ = line[CATEGORY_COL]
        if id_ in categories:
            continue
        category = get_category_info(id_, overrides)
        categories[id_] = category

    for line in links_page_lines:

        child_id = line[CATEGORY_COL]
        parent_id = get_category_parent_id(child_id)

        while child_id:

            if child_id not in categories:
                categories[child_id] = get_category_info(child_id, overrides)

            if parent_id and parent_id not in categories:
                categories[parent_id] = get_category_info(parent_id, overrides)

            if child_id and child_id not in categories:
                categories[child_id] = get_category_info(child_id, overrides)

            if parent_id and child_id:
                if categories[child_id]["parent"] is None:
                    categories[child_id]["parent"] = parent_id
                if child_id not in categories[parent_id]["children"]:
                    categories[parent_id]["children"].append(child_id)

            child_id = parent_id
            parent_id = get_category_parent_id(child_id)

    return categories


def get_links_by_date(lines):
    links = []
    for line in lines:
        links.append(get_link_from_line(line))
    return sorted(links, key=lambda i: i["create_time"], reverse=True)


def render_sitemap(root_path, categories, links_by_category, sitemap_template):
    import pprint    
    with open(join(root_path, "sitemap.xml"), "w") as file:
        file.write(
            sitemap_template.render(
                root_path=root_path,
                links_by_category=links_by_category,
                categories=categories,
                render_date=datetime.date.today(),
                strftime=datetime.date.strftime
            )
        )


def render_categories(base_path, links_by_category, categories, template):
    for id_, links in links_by_category.items():
        category = categories[id_]
        file_path = join(base_path, category["path"], "index.html")
        root_path = get_category_root_path(id_)
        with open(file_path, "w") as file:
            file.write(
                template.render(
                    links=links,
                    root_path=root_path,
                    category=category,
                    categories=categories,
                )
            )
    for id_, category in categories.items():
        if id_ in links_by_category:
            continue
        file_path = join(base_path, category["path"], "index.html")
        root_path = get_category_root_path(id_)
        with open(file_path, "w") as file:
            file.write(
                template.render(
                    links=[],
                    root_path=root_path,
                    category=category,
                    categories=categories,
                )
            )


def render_links(base_path, links_by_category, template):

    cleaner_js = """
        document.getElementsByTagName('header')[0].remove();
        document.getElementsByTagName('script')[0].remove();
        document.getElementsByTagName('script')[0].remove();
        document.getElementsByTagName('script')[0].remove();
        document.getElementsByClassName('utterances')[0].remove();
    """

    safari = webdriver.Safari()
    safari.set_window_size(600, 350)
    for id_, links in links_by_category.items():
        for link in links:
            file_path = join(base_path, link["file_path"])
            image_url = link["file_path"] + ".png"
            with open(file_path, "w") as file:
                file.write(
                    template.render(
                        link=link, root_path=get_category_root_path(id_),
                        image_url=image_url
                    )
                )
            image_path = join(base_path, image_url)
            if not exists(image_path):
                safari.get('file://' + join(base_path, file_path))
                safari.execute_script(cleaner_js)
                safari.save_screenshot(join(base_path, image_url))


def render_home(base_path, link_page_lines, categories, template):
    links = get_links_by_date(link_page_lines)
    last_update = datetime.date.today()
    file_path = join(base_path, "index.html")
    with open(file_path, "w") as file:
        file.write(
            template.render(
                latest_links=links[:20],
                root_path="./",
                categories=categories,
                last_update=last_update,
                num_of_links=len(link_page_lines),
            )
        )


def makedirs(path):
    if exists(path):
        return
    try:
        _makedirs(path)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise


def build(
    document_url=None,
    links_page_name_on_workbook="Bağlantılar",
    categories_page_name_on_workbook="Kategoriler",
    category_template_name="category.html.jinja2",
    home_template_name="home.html.jinja2",
    link_template_name="link.html.jinja2",
    sitemap_template_name="sitemap.xml.jinja2",
    root_path=join(dirname(realpath(__file__)), "docs/")
):
    temp_file = NamedTemporaryFile(suffix=".xlsx")
    temp_file.write(urllib.request.urlopen(DOCUMENT_URL).read())
    workbook = load_workbook(filename=temp_file.name, read_only=True)
    links_page_lines = get_lines(workbook[links_page_name_on_workbook])
    categories_page_lines = get_lines(
        workbook[categories_page_name_on_workbook])
    category_template = env.get_template(category_template_name)
    link_template = env.get_template(link_template_name)
    home_template = env.get_template(home_template_name)    
    links_by_category = get_links_by_category(links_page_lines)
    categories = get_categories(links_page_lines, categories_page_lines)
    create_category_paths(root_path, links_page_lines)
    render_categories(
        root_path, links_by_category, categories, category_template
    )
    render_links(root_path, links_by_category, link_template)
    render_home(root_path, links_page_lines, categories, home_template)

    sitemap_template = env.get_template(sitemap_template_name)
    render_sitemap(root_path, categories, links_by_category, sitemap_template)


build()
