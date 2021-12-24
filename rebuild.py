#!/usr/bin/env python3

"""This cli tool is used for rebuilding link site from Excell sheet that is 
mentioned from it's settings file.

Typical usage example:

  $ python rebuild.py
"""
from __future__ import annotations

import datetime
import errno
import json
import logging
import sys
import urllib.request
from collections import defaultdict
from datetime import datetime as type_date
from distutils.util import strtobool
from os import makedirs as _makedirs, walk, sep as directory_seperator  # noqa
from os.path import dirname, exists, join, realpath, splitext
from shutil import copyfile
from tempfile import NamedTemporaryFile
from typing import List, Any, Callable, Tuple, Dict
from typing import Union, cast
from urllib.parse import urljoin

import jinja2
from dotenv import dotenv_values
from feedgen.feed import FeedGenerator
from jinja2 import Environment, FileSystemLoader, select_autoescape
from jinja2.environment import Template
from openpyxl import load_workbook
from openpyxl.worksheet.worksheet import Worksheet
from selenium import webdriver
from slugify import slugify  # noqa

logger = logging.getLogger()
logger.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)


LINK_COLUMNS: tuple[str, ...] = (
    "title",
    "url",
    "desc",
    "category_str",
    "kind",
    "lang",
    "sender",
    "source",
    "create_time",
)

CATEGORY_COLUMN_INDEX: int = LINK_COLUMNS.index("category_str")
ENV: Dict = dotenv_values(join(dirname(realpath(__file__)), ".env"))

HTMLMIN_KWARGS: Dict[str, bool] = {
    "remove_optional_attribute_quotes": False,
    "remove_comments": True,
}

Line = Tuple[Any]


def processor_fallback(text: str, **kwargs: List[Any]) -> str:
    """This is a fallback function for any kind of text processors like \
    cssmin or htmlmin. Only thing that it does is returning the text back.

    Returns:
        str:  Same string given from parameter.
    """
    return text


if strtobool(cast(str, ENV.get("MINIMIZE_CSS", "True"))):
    try:
        from rcssmin import cssmin
    except ImportError:
        cssmin: Callable = processor_fallback
        logger.warning(
            "Could not import rcssmin. CSS files will not be compressed."
        )


if strtobool(cast(str, ENV.get("MINIMIZE_HTML", "True"))):
    try:
        from htmlmin import minify as htmlmin
    except ImportError:
        htmlmin: Callable = processor_fallback
        logger.warning(
            "Could not import htmlmin. HTML files will not be compressed."
        )


def get_lines(worksheet: Worksheet) -> List[List[Union[str, None, type_date]]]:
    """Load lines from worksheet and return as list of lists.

    :param worksheet: Worksheet Object
    :return: list
    """
    logger.debug("Parsing lines from worksheet.")
    result: List[List[Union[str, None, type_date]]] = []
    for idx, row in enumerate(worksheet.rows):
        if idx == 0:
            continue
        result.append(tuple(map(lambda cell: cell.value, row)))
    return result


def get_category_parts(category_str: str) -> List[str]:
    """Separate category to list items.

    Args:
        category_str: String representation of a category.

    Returns:
        List of strings that contains every part of given category.

    >>> category_str = 'a > b > c'
    >>> get_category_parts(category_str)
    ['a', 'b', 'c']

  """
    separator = ENV["SPREADSHEET_CATEGORY_SEPARATOR"]
    return list(
        filter(
            lambda part: bool(part),
            [part.strip() for part in category_str.split(separator)],
        )
    )


def get_category_path(category_str: str) -> str:
    """
    Convert category string to a path.

    :param category_str: String representing a category.
    :return: path string.

    >>> category_str = 'a > b > c'
    >>> get_category_path(category_str)
    'a/b/c/'
    """
    parts = get_category_parts(category_str)
    return ("/".join(map(slugify, parts))) + "/"


def get_category_root_path(category_str: str) -> str:
    """
    Get relative root path for category.

    :param category_str: String representing a category.
    :return: Relative path that points to root directory.

    >>> category_str = 'a > b > c'
    >>> get_category_root_path(category_str)
    '../../../'
    """
    return "../" * (get_category_depth(category_str) + 1)


def get_category_depth(category_str: str) -> int:
    """
    Get depth of a category.

    :param category_str: String representing a category.
    :return: Integer that describes depth of the category.

    >>> category_str = 'a > b > c'
    >>> get_category_depth(category_str)
    2
    """
    return category_str.count(cast(str, ENV["SPREADSHEET_CATEGORY_SEPARATOR"]))


def get_parent_category_str(category_str: str) -> str | None:
    """
    Get parent category str of category_str.

    :param category_str: String representing a category.
    :return: String representing parent category.

    >>> category_str = 'a > b > c'
    >>> get_parent_category_str(category_str)
    'a > b'
    """
    if category_str is None:
        return None
    parts = get_category_parts(category_str)
    return (
        f" {ENV['SPREADSHEET_CATEGORY_SEPARATOR']} ".join(parts[:-1])
        if len(parts) > 1
        else None
    )


def get_link_from_row(link_row):
    """
    Get link information from a line in worksheet.

    :param link_row: List of items that represents a row in links page.
    :return: Dictionary that contaıns lınk informatıon

    >>> link_row = (
    ...     "Google",
    ...     "https://google.com",
    ...     "Most popular search engine",
    ...     "internet > search engines",
    ...     "website",
    ...     "English",
    ...     "mirat",
    ...     "reddit",
    ...     datetime.datetime(1984, 7, 10),
    ... )
    >>> get_link_from_row(link_row)
    {'title': 'Google', 'url': 'https://google.com', \
'desc': 'Most popular search engine', \
'category_str': 'internet > search engines', 'kind': 'website', \
'lang': 'English', 'sender': 'mirat', 'source': 'reddit', \
'create_time': datetime.datetime(1984, 7, 10, 0, 0, \
tzinfo=datetime.timezone(datetime.timedelta(seconds=10800))), \
'file_path': 'internet/search-engines/https-google-com.html'}
    """
    link = {
        column: link_row[index] for index, column in enumerate(LINK_COLUMNS)
    }
    if link["create_time"] is None:
        raise ValueError("Line %s has missing create_time value." % line)
    link["create_time"] = link["create_time"].replace(
        tzinfo=datetime.timezone(
            datetime.timedelta(hours=int(ENV.get("TIMEZONE_HOURS", "3")))
        )
    )
    link["file_path"] = (
        get_category_path(link_row[CATEGORY_COLUMN_INDEX])
        + slugify(link["url"])
        + ".html"
    )
    return link


def get_links_by_category(link_rows: List[List[Union[str, type_date, None]]]) -> Dict[str, List[Dict[str, Union[str, None, type_date]]]]:
    """
    Get links by grouping them by their category string.

    :param link_rows: List of lists that represents rows in links page.
    :return: Dictionary that contaıns grouped links.

    >>> link_row_1 = (
    ...     "Google",
    ...     "https://google.com",
    ...     "Most popular search engine",
    ...     "internet > search engines",
    ...     "website",
    ...     "English",
    ...     "mirat",
    ...     "reddit",
    ...     datetime.datetime(1984, 7, 10),
    ... )

    >>> link_row_2 = (
    ...     "Gmail",
    ...     "https://gmail.com",
    ...     "Most popular email service",
    ...     "internet > email providers",
    ...     "website",
    ...     "English",
    ...     "mirat",
    ...     "reddit",
    ...     datetime.datetime(1984, 7, 10),
    ... )

    >>> links_by_category = get_links_by_category([link_row_1, link_row_2])

    >>> "internet > email providers" in links_by_category
    True

    >>> len(links_by_category["internet > email providers"]) == 1
    True

    >>> links_by_category["internet > email providers"][0]['title'] == 'Gmail'
    True

    >>> "internet > search engines" in links_by_category
    True

    >>> len(links_by_category["internet > search engines"]) == 1
    True

    >>> links_by_category["internet > search engines"][0]['title'] == 'Google'
    True
    """
    logger.debug("Building links by category.")
    result: Dict[str, List[Dict[str, Union[str, type_date, None]]]] = defaultdict(list)
    for link_row in link_rows:
        category_str: str = link_row[CATEGORY_COLUMN_INDEX]
        link = get_link_from_row(link_row)
        result[category_str].append(link)
    return result


def create_category_paths(base_path, category_str_list, dry=False):
    """
    Create directories of categories

    :param base_path: String that represents path of building directory.
    :param category_str_list: String that represents path of building directory.

    :return: List of strings that represents paths of created directories.

    >>> base_path = '/tmp/'
    >>> category_str_list = ['a > b', 'a > c', 'b > c']

    >>> create_category_paths(base_path, category_str_list)
    ['/tmp/a/b/', '/tmp/a/c/', '/tmp/b/c/']
    """
    logger.debug("Creating category paths.")
    created_dirs = []
    for category_str in category_str_list:
        path = join(base_path, get_category_path(category_str))
        if not dry:
            make_dirs(path)
        created_dirs.append(path)
    return created_dirs

def get_category_overrides(categories_page_rows):
    """
    Get optional title and description information of categories from categories page in spreadsheet.

    :param categories_page_rows: List of lists that represent lines on
    categories page.
    :return: Dictionary that contains title and descriptions of categories.

    >>> category_line_1 = ['a', 'Title of Category A', 'Desc of Category A']

    >>> category_line_2 = ['b', 'Title of Category B', 'Desc of Category B']

    >>> get_category_overrides([category_line_1, category_line_2])
    {'a': {'title': 'Title of Category A', 'desc': 'Desc of Category A'}, \
'b': {'title': 'Title of Category B', 'desc': 'Desc of Category B'}}
    """
    logger.debug("Getting category overrides.")
    overrides: Dict[str, str]= {}
    for category_page_row in categories_page_rows:
        override = {}
        if len(category_page_row) > 1 and category_page_row[1] is not None:
            override["title"] = category_page_row[1]
        if len(category_page_row) > 2 and category_page_row[2] is not None:
            override["desc"] = category_page_row[2]
        overrides[category_page_row[0]] = override

    return overrides


def get_category_info(category_str: str, overrides: Dict[str, Dict[str, str]]):
    """
    Get information of single category.

    >>> overrides = {\
    'a': {'title': 'Title of category "a" overrided by this.'},\
    'b': {'desc': 'Description of Category "b" overrided by this.'}\
    }

    >>> get_category_info('a', overrides)
    {'name': 'a', 'title': 'Title of category "a" overrided by this.', \
'desc': None, 'parent': None, 'path': 'a/', 'children': []}

    >>> get_category_info('b', overrides)
    {'name': 'b', 'title': 'b', 'desc': 'Description of Category "b" \
overrided by this.', 'parent': None, 'path': 'b/', 'children': []}
    """
    name = get_category_parts(category_str)[-1]
    result: Dict[str, Union[str, None, List[None]]] = {
        "name": name,
        "title": name,
        "desc": None,
        "parent": None,
        "path": get_category_path(category_str),
        "children": [],
    }
    result.update(overrides.get(category_str, {}))
    return result


def get_categories(links_page_rows, categories_page_rows: List[List[Union[str, None]]]):
    logger.info("Building category information.")
    categories = {}
    overrides = get_category_overrides(categories_page_rows)

    # Warn about missing categories on categories page.

    categories_of_links = [r[CATEGORY_COLUMN_INDEX] for r in links_page_rows]
    categories_of_overrides = list(overrides.keys())
    missing_categories = set(categories_of_overrides) - set(categories_of_links)
    for missing_category in missing_categories:
        logger.warning(
            'Category: "%s" appears on category overrides page '
            "but there's no links associated with it",
            missing_category,
        )

    for row in links_page_rows:
        category_str = row[CATEGORY_COLUMN_INDEX]
        if category_str in categories:
            continue
        category = get_category_info(category_str, overrides)
        categories[category_str] = category

    for row in links_page_rows:

        child_category_str: str = row[CATEGORY_COLUMN_INDEX]
        parent_category_str = get_parent_category_str(child_category_str)

        while child_category_str:

            if child_category_str not in categories:
                categories[child_category_str] = get_category_info(
                    child_category_str, overrides
                )

            if parent_category_str and parent_category_str not in categories:
                categories[parent_category_str] = get_category_info(
                    parent_category_str, overrides
                )

            if child_category_str and child_category_str not in categories:
                categories[child_category_str] = get_category_info(
                    child_category_str, overrides
                )

            if parent_category_str and child_category_str:
                if categories[child_category_str]["parent"] is None:
                    categories[child_category_str][
                        "parent"
                    ] = parent_category_str
                if (
                    child_category_str
                    not in categories[parent_category_str]["children"]
                ):
                    categories[parent_category_str]["children"].append(
                        child_category_str
                    )

            child_category_str = parent_category_str
            parent_category_str = get_parent_category_str(child_category_str)

    return categories


def get_links_by_date(link_rows, reverse=True):
    """
    Get links from rows of links page on spreadsheet and order them by their
    create time.

    >>> link_row_1 = (
    ...     "Google",
    ...     "https://google.com",
    ...     "Most popular search engine",
    ...     "internet > search engines",
    ...     "website",
    ...     "English",
    ...     "mirat",
    ...     "reddit",
    ...     datetime.datetime(2020, 1, 1),
    ... )

    >>> link_row_2 = (
    ...     "Gmail",
    ...     "https://gmail.com",
    ...     "Most popular email service",
    ...     "internet > email providers",
    ...     "website",
    ...     "English",
    ...     "mirat",
    ...     "reddit",
    ...     datetime.datetime(2019, 1, 2),
    ... )

    >>> get_links_by_date([link_row_1, link_row_2])
    {}
    """
    links = []
    for row in link_rows:
        links.append(get_link_from_row(row))
    return sorted(links, key=lambda i: i["create_time"], reverse=reverse)


def render_sitemap(root_path: str, categories: Dict[str, Union[str, None, List[str]]],
                    links_by_category: Dict[str, List[Dict[str, Union[str, None, type_date]]]],
                    sitemap_template: Template):

    logger.info("Rendering sitemap.")
    with open(join(root_path, "sitemap.xml"), "w") as file:
        file.write(
            htmlmin(
                sitemap_template.render(
                    root_path=root_path,
                    links_by_category=links_by_category,
                    categories=categories,
                    render_date=datetime.date.today(),
                    strftime=datetime.date.strftime,
                ),
                **HTMLMIN_KWARGS,
            )
        )


def render_feed(root_path: str, link_page_rows):
    logger.info("Rendering feed outputs.")
    feed = FeedGenerator()
    feed.id(ENV["SITE_URL"])
    feed.title(ENV["SITE_TITLE"])
    feed.link(href=ENV["SITE_URL"], rel="alternate")
    feed.subtitle(ENV["SITE_DESC"])
    feed.link(href=urljoin(ENV["SITE_URL"], "feed.rss"), rel="self")
    feed.language("tr")

    links = get_links_by_date(link_page_rows)
    for link in links:
        entry = feed.add_entry()
        entry.id(link["file_path"])
        entry.title(link["title"])
        entry.description(link["desc"])
        entry.link(
            title=link["title"],
            rel="alternate",
            type="text/html",
            href=urljoin(ENV["SITE_URL"], link["file_path"]),
        )
        entry.updated(link["create_time"])
    feed.rss_file(join(root_path, "rss.xml"), pretty=True)
    feed.atom_file(join(root_path, "atom.xml"), pretty=True)


def render_categories(base_path: str, links_by_category: Dict[str, List[Dict[str, Union[str, None, type_date]]]], categories, template):
    logger.info("Rendering categories.")
    for category_str, links in links_by_category.items():
        category = categories[category_str]
        file_path: str = join(base_path, cast(str, category["path"]), "index.html")
        root_path: str = get_category_root_path(category_str)
        with open(file_path, "w") as file:
            file.write(
                htmlmin(
                    template.render(
                        site_title=ENV["SITE_TITLE"],
                        links=links,
                        root_path=root_path,
                        category=category,
                        categories=categories,
                        env=ENV,
                    ),
                    **HTMLMIN_KWARGS,
                )
            )
    for category_str, category in categories.items():
        if category_str in links_by_category:
            continue
        file_path = join(base_path, category["path"], "index.html")
        root_path = get_category_root_path(category_str)
        with open(file_path, "w") as file:
            file.write(
                htmlmin(
                    template.render(
                        links=[],
                        root_path=root_path,
                        category=category,
                        categories=categories,
                        env=ENV,
                    ),
                    **HTMLMIN_KWARGS,
                )
            )


def get_browser():
    web_drivers: tuple[str, ...] = ("Firefox", "Chrome", "Safari")
    drivers: tuple[str, ...] = ("geckodriver", "chromedriver", "safari")

    for web_driver, driver in zip(web_drivers, drivers):
        try:
            if exists(driver):
                browser = getattr(webdriver, web_driver)(
                    executable_path=f"./{driver}"
                )
            else:
                browser = getattr(webdriver, web_driver)()

            browser.set_window_size(600, 400)
            return browser
        except Exception as err:
            logger.error(err)
            continue


def render_links(base_path: str, links_by_category: Dict[str, List[Dict[str, Union[str, None, type_date]]]], template: Template):
    logger.info("Rendering links.")
    force = strtobool(cast(str, ENV.get("FORCE_SCREENSHOT", "False")))
    cleaner_js:str = """
        document.getElementsByTagName('header')[0].style.background='none';
        document.getElementsByTagName('form')[0].remove();
        document.getElementById('page').style.margin=0;
        document.getElementById('link_detail').style.margin=0;
        text = document.getElementsByTagName('h1')[0].textContent;
        document.getElementsByTagName('h1')[0].textContent = text.toUpperCase();
        document.getElementsByTagName('header')[0].style.background='none';
        document.getElementsByTagName('script')[0].remove();
        document.getElementsByClassName('meta')[0].remove();
        document.getElementsByClassName('socializer')[0].remove()
        document.getElementsByTagName('p')[1].classList.remove('mb');
    """
    browser = None
    for category_str, links in links_by_category.items():
        for link in links:
            file_path = join(base_path, cast(str, link["file_path"]))
            image_url: str = f"{link['file_path']}.png"
            with open(file_path, "w") as file:
                file.write(
                    htmlmin(
                        template.render(
                            link=link,
                            root_path=get_category_root_path(category_str),
                            image_url=image_url,
                            env=ENV,
                        ),
                        **HTMLMIN_KWARGS,
                    )
                )
            image_path = join(base_path, image_url)
            if force or not exists(image_path):
                if not browser:
                    browser = get_browser()
                    if browser is None:
                        logger.info(
                            "Not able to run Selenium. "
                            "Screenshots will not be generated."
                        )
                        return

                browser.get("file://" + join(base_path, file_path))
                browser.execute_script(cleaner_js)
                browser.save_screenshot(join(base_path, image_url))

    if browser:
        browser.close()


def render_home(base_path: str, link_page_rows: List[List[Union[str, None, type_date]]],
                categories: Dict[str, Union[str, None, List[str]]],
                template: jinja2.Template):

    logger.info("Rendering homepage.")
    links = get_links_by_date(link_page_rows)
    last_update = datetime.date.today()
    file_path = join(base_path, "index.html")
    with open(file_path, "w") as file:
        file.write(
            htmlmin(
                template.render(
                    latest_links=links[:50],
                    root_path="./",
                    categories=categories,
                    last_update=last_update,
                    num_of_links=len(link_page_rows),
                    env=ENV,
                ),
                **HTMLMIN_KWARGS,
            )
        )


def make_dirs(path: str):
    if exists(path):
        return
    try:
        _makedirs(path)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise


def build_assets(build_path: str, assets_path: str):
    # Todo: Find any 
    processors: Dict[str, Any] = {".css": (cssmin, {}), ".html": (htmlmin, HTMLMIN_KWARGS)}
    logger.info("Building assets.")
    for root, _, file_names in walk(assets_path):
        target_dir = join(build_path, *root.split(directory_seperator)[2:])
        make_dirs(target_dir)
        for file_name in file_names:
            source_file_path = join(root, file_name)
            target_file_path = join(target_dir, file_name)
            logger.debug(
                "Processing asset: %s -> %s"
                % (source_file_path, target_file_path)
            )
            extension = splitext(file_name)[1]
            processor, kwargs = processors.get(extension, (None, {}))
            if not processor:
                copyfile(source_file_path, target_file_path)
                continue
            with open(source_file_path, "r") as file:
                content = file.read()
            content = processor(content, **kwargs)
            with open(target_file_path, "w") as file:
                file.write(content)


def render_json(root_path: str, categories: Dict[str, Union[str, None, List[str]] ], links_by_category: Dict[str, List[Dict[str, Union[str, None, type_date]]]]):
    logger.info("Building json output.")

    class DateTimeEncoder(json.JSONEncoder):
        def default(self, o):
            if isinstance(o, datetime.datetime):
                return o.isoformat()
            return json.JSONEncoder.default(self, o)

    with open(join(root_path, "data.json"), "w", encoding="utf8") as file:
        data = {
            "categories": categories,
            "links_by_category": links_by_category,
        }
        json.dump(data, file, cls=DateTimeEncoder, ensure_ascii=False)


def build(build_path: str =join(dirname(realpath(__file__)), "docs/")):
    jinja = Environment(
        loader=FileSystemLoader("templates/"),
        autoescape=select_autoescape(["html", "xml"]),
    )

    with NamedTemporaryFile(suffix=".xlsx") as spreadsheet_file:
        with urllib.request.urlopen(cast(str,ENV["SPREADSHEET_URL"])) as remote_file:
            spreadsheet_file.write(remote_file.read())
            workbook = load_workbook(
                filename=spreadsheet_file.name, read_only=True
            )

    links_page_lines = get_lines(
        workbook[cast(str, ENV.get("SPREADSHEET_LINKS_PAGE_NAME", "Links"))]
    )

    categories_page_lines = get_lines(
        workbook[cast(str, ENV.get("SPREADSHEET_CATEGORIES_PAGE_NAME", "Categories"))]
    )

    category_template = jinja.get_template("category.html.jinja2")
    link_template = jinja.get_template("link.html.jinja2")
    home_template = jinja.get_template("home.html.jinja2")
    sitemap_template = jinja.get_template("sitemap.xml.jinja2")

    links_by_category = get_links_by_category(links_page_lines)
    categories = get_categories(links_page_lines, categories_page_lines)

    category_str_list = [r[CATEGORY_COLUMN_INDEX] for r in links_page_lines]
    create_category_paths(build_path, category_str_list)

    render_json(build_path, categories, links_by_category)
    build_assets(build_path, "./assets/")
    render_categories(
        build_path, links_by_category, categories, category_template
    )
    render_links(build_path, links_by_category, link_template)
    render_home(build_path, links_page_lines, categories, home_template)
    render_sitemap(build_path, categories, links_by_category, sitemap_template)
    render_feed(build_path, links_page_lines)


if __name__ == "__main__":
    build()
