#!/usr/bin/env python3

"""This cli tool is used for rebuilding link site from Excel sheet that is
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
from dataclasses import dataclass
from dataclasses import asdict as dataclass_as_dict
from datetime import datetime as type_date
from functools import lru_cache
from os import makedirs as _makedirs, walk, sep as directory_seperator  # noqa
from os.path import dirname, exists, join, realpath, splitext
from shutil import copyfile
from tempfile import NamedTemporaryFile
from typing import List, Any, Callable, Tuple, Dict
from typing import Union, cast
from urllib.parse import urljoin

from dotenv import dotenv_values
from feedgen.feed import FeedGenerator
from jinja2 import Environment, FileSystemLoader, select_autoescape, Template
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

STR_TO_BOOLEAN_MAP: Dict[str, bool] = {
    "y": True,
    "yes": True,
    "t": True,
    "true": True,
    "on": True,
    "1": True,
    "n": False,
    "no": False,
    "f": False,
    "false": False,
    "off": False,
    "0": False,
}

LINK_COLUMNS: tuple[str, ...] = (
    "line_number",
    "title",
    "url",
    "desc",
    "category_id",
    "kind",
    "lang",
    "sender",
    "source",
    "create_time",
)

REQUIRED_COLUMNS: tuple[str, ...] = (
    "title",
    "url",
    "desc",
    "category_id",
    "kind",
    "lang",
    "create_time",
)


@dataclass
class Link:
    row_number: int
    title: str
    url: str
    desc: str
    category_id: str
    kind: str
    lang: str
    sender: str
    source: str
    create_time: type_date
    file_path: str

    def __repr__(self):
        return f"Link('{self.url}')"


ENV: Dict = dotenv_values(join(dirname(realpath(__file__)), ".env"))

HTMLMIN_KWARGS: Dict[str, bool] = {
    "remove_optional_attribute_quotes": False,
    "remove_comments": True,
}

LinkRow = Tuple[int, str, str, str, str, str, str, str, str, type_date]
CategoryRow = Tuple[int, str, str, str]
CategoryOverrides = Dict[str, Dict[str, str]]
LinksByCategory = Dict[str, List[Link]]


def strtobool(value):
    try:
        return STR_TO_BOOLEAN_MAP[str(value).lower()]
    except KeyError:
        raise ValueError('"{}" is not a valid bool value'.format)


def processor_fallback(text: str, **kwargs: List[Any]) -> str:  # noqa
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
        logger.warning("Could not import rcssmin. CSS files will not be compressed.")


if strtobool(cast(str, ENV.get("MINIMIZE_HTML", "True"))):
    try:
        from htmlmin import minify as htmlmin
    except ImportError:
        htmlmin: Callable = processor_fallback
        logger.warning("Could not import htmlmin. HTML files will not be compressed.")


@lru_cache(maxsize=len(LINK_COLUMNS))
def get_column_index(key: str) -> int:
    try:
        return LINK_COLUMNS.index(key)
    except ValueError:
        raise ValueError(f"Invalid column name: {key}")


def get_rows(worksheet: Worksheet) -> List[LinkRow]:
    """Load lines from worksheet and return as list of lists.

    :param worksheet: Worksheet Object
    :return: list
    """
    logger.debug("Parsing lines from worksheet.")
    result: List[LinkRow] = []
    for idx, row in enumerate(worksheet.rows):
        if idx == 0:
            continue
        result.append((idx,) + tuple(map(lambda cell: cell.value, row)))
    return result


def get_category_parts(category_id: str) -> List[str]:
    """Separate category to list items.

    Args:
        category_id: String representation of a category.

    Returns:
        List of strings that contains every part of given category.

    >>> get_category_parts('a > b > c')
    ['a', 'b', 'c']
    """
    separator = ENV["SPREADSHEET_CATEGORY_SEPARATOR"]
    return list(
        filter(
            lambda part: bool(part),
            [part.strip() for part in category_id.split(separator)],
        )
    )


def get_category_path(category_id: str) -> str:
    """
    Convert category string to a path.

    :param category_id: String representing a category.
    :return: path string.

    >>> get_category_path('a > b > c')
    'a/b/c/'
    """
    parts = get_category_parts(category_id)
    return ("/".join(map(slugify, parts))) + "/"


def get_category_root_path(category_id: str) -> str:
    """
    Get relative root path for category.

    :param category_id: String representing a category.
    :return: Relative path that points to root directory.

    >>> get_category_root_path('a > b > c')
    '../../../'
    """
    return "../" * (get_category_depth(category_id) + 1)


def get_category_depth(category_id: str) -> int:
    """
    Get depth of a category.

    :param category_id: String representing a category.
    :return: Integer that describes depth of the category.

    >>> get_category_depth('a > b > c')
    2
    """
    return category_id.count(cast(str, ENV["SPREADSHEET_CATEGORY_SEPARATOR"]))


def get_parent_category_id(category_id: str) -> str | None:
    """
    Get parent category str of category_id.

    :param category_id: String representing a category.
    :return: String representing parent category.

    >>> get_parent_category_id('a > b > c')
    'a > b'
    """
    if category_id is None:
        return None
    parts = get_category_parts(category_id)
    return (
        f" {ENV['SPREADSHEET_CATEGORY_SEPARATOR']} ".join(parts[:-1])
        if len(parts) > 1
        else None
    )


def get_link_from_row(row: LinkRow) -> Link:
    """
    Get link information from a row in worksheet.

    :param row: List of items that represents a row in links page.
    :return: Dictionary that contaıns lınk informatıon

    >>> link_row_0 = (
    ...     0,
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
    >>> get_link_from_row(link_row_0)
    Link('https://google.com')
    """
    link = Link(
        row[get_column_index("line_number")],
        row[get_column_index("title")],
        row[get_column_index("url")],
        row[get_column_index("desc")],
        row[get_column_index("category_id")],
        row[get_column_index("kind")],
        row[get_column_index("lang")],
        row[get_column_index("sender")],
        row[get_column_index("source")],
        row[get_column_index("create_time")].replace(
            tzinfo=datetime.timezone(
                datetime.timedelta(hours=int(ENV.get("TIMEZONE_HOURS", "3")))
            )
        ),
        get_category_path(row[get_column_index("category_id")])
        + slugify(row[get_column_index("url")])
        + ".html",
    )
    return link


def get_links_by_category(link_rows: List[LinkRow]) -> LinksByCategory:
    """
    Get links by grouping them by their category string.

    :param link_rows: List of lists that represents rows in links page.
    :return: Dictionary that contains grouped links.

    >>> link_row_0 = (
    ...     0,
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

    >>> link_row_1 = (
    ...     1,
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

    >>> links_by_category = get_links_by_category([link_row_0, link_row_1])
    >>> "internet > email providers" in links_by_category
    True

    >>> len(links_by_category["internet > email providers"]) == 1
    True

    >>> links_by_category["internet > email providers"][0].title == 'Gmail'
    True

    >>> "internet > search engines" in links_by_category
    True

    >>> len(links_by_category["internet > search engines"]) == 1
    True

    >>> links_by_category["internet > search engines"][0].title == 'Google'
    True
    """
    logging.debug("Building links by category.")
    result: Dict[str, List[Link]] = defaultdict(list)
    for link_row in link_rows:
        category_id: str = link_row[get_column_index("category_id")]
        link = get_link_from_row(link_row)
        result[category_id].append(link)
    return result


def create_category_paths(base_path, categories: List[str], dry=False):
    """
    Create directories of categories

    :param base_path: String that represents path of building directory.
    :param categories: String that represents path of building directory.
    :param dry: Don't really create paths.

    :return: List of strings that represents paths of created directories.

    >>> category_ids = ['a > b', 'a > c', 'b > c']

    >>> create_category_paths('/tmp/', category_ids)
    ['/tmp/a/b/', '/tmp/a/c/', '/tmp/b/c/']
    """
    logger.debug("Creating category paths.")
    created_dirs = []
    for category in categories:
        path = join(base_path, get_category_path(category))
        if not dry:
            make_dirs(path)
        created_dirs.append(path)
    return created_dirs


def get_category_breadcrumbs(category_id, categories):
    category_parts = get_category_parts(category_id)
    breadcrumbs = []
    for i in range(0, len(category_parts)):
        breadcrumb_id = " > ".join(category_parts[: i + 1])
        breadcrumbs.append(categories[breadcrumb_id])
    return breadcrumbs


def get_category_overrides(categories_page_rows) -> CategoryOverrides:
    """
    Get optional title and description information of categories from
    categories page in spreadsheet.

    :param categories_page_rows: List of lists that represent lines on
    categories page.
    :return: Dictionary that contains title and descriptions of categories.

    >>> category_line_0 = [0, 'a', 'Title Category A', 'Desc Category A']
    >>> category_line_1 = [1, 'b', 'Title Category B', 'Desc Category B']
    >>> get_category_overrides([category_line_0, category_line_1])
    {'a': {'title': 'Title of Category A', 'desc': 'Desc of Category A'}, \
'b': {'title': 'Title of Category B', 'desc': 'Desc of Category B'}}
    """
    logger.debug("Getting category overrides.")
    overrides = {}
    for category_page_row in categories_page_rows:
        override = {}
        if len(category_page_row) > 2 and category_page_row[2] is not None:
            override["title"] = category_page_row[2]
        if len(category_page_row) > 3 and category_page_row[3] is not None:
            override["desc"] = category_page_row[3]
        overrides[category_page_row[1]] = override
    return overrides


def get_category_info(category_id: str, overrides: CategoryOverrides) -> Dict:
    """
    Get information of single category.

    >>> _overrides = {
    'a': {'title': 'Title of category "a" overridden by this.'},\
    'b': {'desc': 'Description of Category "b" overridden by this.'}\
    }

    >>> get_category_info('a', _overrides)
    {'name': 'a', 'title': 'Title of category "a" overrided by this.', \
'desc': None, 'parent': None, 'path': 'a/', 'children': []}

    >>> get_category_info('b', _overrides)
    {'name': 'b', 'title': 'b', 'desc': 'Description of Category "b" \
overrided by this.', 'parent': None, 'path': 'b/', 'children': []}
    """
    name = get_category_parts(category_id)[-1]
    result: Dict[str, Union[str, None, List[None]]] = {
        "name": name,
        "title": name,
        "desc": None,
        "parent": None,
        "id": category_id,
        "path": get_category_path(category_id),
        "children": [],
    }
    result.update(overrides.get(category_id, {}))
    return result


def get_categories(
    links_page_rows: List[LinkRow], categories_page_rows: List[LinkRow]
) -> Dict:
    logger.info("Building category information.")
    categories = {}
    overrides = get_category_overrides(categories_page_rows)
    categories_of_links = [r[get_column_index("category_id")] for r in links_page_rows]
    categories_of_overrides = list(overrides.keys())
    missing_categories = set(categories_of_overrides) - set(categories_of_links)
    for missing_category in missing_categories:
        logger.warning(
            'Category: "%s" appears on category overrides page '
            "but there's no links associated with it",
            missing_category,
        )

    for row in links_page_rows:
        category_id = row[get_column_index("category_id")]
        if category_id in categories:
            continue
        category = get_category_info(category_id, overrides)
        categories[category_id] = category

    for row in links_page_rows:

        child_category_id: str = row[get_column_index("category_id")]
        parent_category_id = get_parent_category_id(child_category_id)

        while child_category_id:

            if child_category_id not in categories:
                categories[child_category_id] = get_category_info(
                    child_category_id, overrides
                )

            if parent_category_id and parent_category_id not in categories:
                categories[parent_category_id] = get_category_info(
                    parent_category_id, overrides
                )

            if child_category_id and child_category_id not in categories:
                categories[child_category_id] = get_category_info(
                    child_category_id, overrides
                )

            if parent_category_id and child_category_id:
                if categories[child_category_id]["parent"] is None:
                    categories[child_category_id]["parent"] = parent_category_id
                if (
                    child_category_id
                    not in categories[parent_category_id]["children"]
                ):
                    categories[parent_category_id]["children"].append(
                        child_category_id
                    )

            child_category_id = parent_category_id
            parent_category_id = get_parent_category_id(child_category_id)

    return categories


def get_links_by_date(link_rows, reverse=True):
    """
    Get links from rows of links page on spreadsheet and order them by their
    create time.

    >>> link_row_1 = (
    ...     0,
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
    ...     1,
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
    [Link('https://google.com'), Link('https://gmail.com')]
    """
    links = []
    for row in link_rows:
        links.append(get_link_from_row(row))
    return sorted(links, key=lambda i: i.create_time, reverse=reverse)


def render_sitemap(
    root_path: str,
    categories: Dict[str, Union[str, None, List[str]]],
    links_by_category: LinksByCategory,
    sitemap_template: Template,
):

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


def render_feed(root_path: str, link_page_rows: List[LinkRow]):
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
        entry.id(link.file_path)
        entry.title(link.title)
        entry.description(link.desc)
        entry.link(
            title=link.title,
            rel="alternate",
            type="text/html",
            href=urljoin(ENV["SITE_URL"], link.file_path),
        )
        entry.updated(link.create_time)
    feed.rss_file(join(root_path, "rss.xml"), pretty=True)
    feed.atom_file(join(root_path, "atom.xml"), pretty=True)


def render_categories(
    base_path: str,
    links_by_category: LinksByCategory,
    categories,
    template,
):
    logger.info("Rendering categories.")
    for category_id, links in links_by_category.items():
        category = categories[category_id]
        file_path: str = join(base_path, cast(str, category["path"]), "index.html")
        root_path: str = get_category_root_path(category_id)
        breadcrumbs: list = get_category_breadcrumbs(category_id, categories)
        with open(file_path, "w") as file:
            file.write(
                htmlmin(
                    template.render(
                        site_title=ENV["SITE_TITLE"],
                        links=links,
                        root_path=root_path,
                        category=category,
                        categories=categories,
                        breadcrumbs=breadcrumbs,
                        env=ENV,
                    ),
                    **HTMLMIN_KWARGS,
                )
            )
    for category_id, category in categories.items():
        if category_id in links_by_category:
            continue
        file_path = join(base_path, category["path"], "index.html")
        root_path = get_category_root_path(category_id)
        breadcrumbs: list = get_category_breadcrumbs(category_id, categories)
        with open(file_path, "w") as file:
            file.write(
                htmlmin(
                    template.render(
                        links=[],
                        root_path=root_path,
                        category=category,
                        categories=categories,
                        breadcrumbs=breadcrumbs,
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
                browser = getattr(webdriver, web_driver)(executable_path=f"./{driver}")
            else:
                browser = getattr(webdriver, web_driver)()

            browser.set_window_size(600, 400)
            return browser
        except Exception as err:
            logger.error(err)
            continue


def render_links(
    base_path: str,
    links_by_category: LinksByCategory,
    categories: Categories,
    template: Template,
):
    logger.info("Rendering links.")
    force = strtobool(cast(str, ENV.get("FORCE_SCREENSHOT", "False")))
    cleaner_js: str = """
        document.getElementsByTagName('header')[0].style.background='none';
        document.getElementsByTagName('form')[0].remove();
        document.getElementById('page').style.margin=0;
        document.getElementById('link_detail').style.margin=0;
        text = document.getElementsByTagName('h1')[0].textContent;
        document.getElementsByTagName('h1')[0].textContent=text.toUpperCase();
        document.getElementsByTagName('header')[0].style.background='none';
        document.getElementsByTagName('script')[0].remove();
        document.getElementsByClassName('meta')[0].remove();
        document.getElementsByClassName('socializer')[0].remove()
        document.getElementsByTagName('p')[1].classList.remove('mb');
    """
    browser = get_browser()
    if browser is None:
        logger.info("Not able to run Selenium. " "Screenshots will not be generated.")
    for category_id, links in links_by_category.items():
        for link in links:
            file_path = join(base_path, cast(str, link.file_path))
            image_url: str = f"{link.file_path}.png"
            breadcrumbs: list = get_category_breadcrumbs(category_id, categories)
            with open(file_path, "w") as file:
                file.write(
                    htmlmin(
                        template.render(
                            link=link,
                            root_path=get_category_root_path(category_id),
                            breadcrumbs=breadcrumbs,
                            image_url=image_url,
                            env=ENV,
                        ),
                        **HTMLMIN_KWARGS,
                    )
                )
            logger.debug(f"{file_path} written.")
            image_path = join(base_path, image_url)
            if force or not exists(image_path) and browser:
                browser.get("file://" + join(base_path, file_path))
                browser.execute_script(cleaner_js)
                browser.save_screenshot(join(base_path, image_url))
    if browser:
        browser.close()


def render_home(
    base_path: str,
    link_rows: List[LinkRow],
    categories: Dict[str, Union[str, None, List[str]]],
    template: Template,
):

    logger.info("Rendering homepage.")
    links = get_links_by_date(link_rows)
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
                    num_of_links=len(link_rows),
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
    processors: Dict[str, Tuple[Callable, Dict]] = {
        ".css": (cssmin, {}),
        ".html": (htmlmin, HTMLMIN_KWARGS),
    }
    logger.info("Building assets.")
    for root, _, file_names in walk(assets_path):
        target_dir = join(build_path, *root.split(directory_seperator)[2:])
        make_dirs(target_dir)
        for file_name in file_names:
            source_file_path = join(root, file_name)
            target_file_path = join(target_dir, file_name)
            logger.debug(
                "Processing asset: %s -> %s" % (source_file_path, target_file_path)
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


def render_json(
    root_path: str,
    categories: Dict[str, Union[str, None, List[str]]],
    links_by_category: LinksByCategory,
):
    logger.info("Building json output.")

    class DateTimeEncoder(json.JSONEncoder):
        def default(self, o):
            if isinstance(o, datetime.datetime):
                return o.isoformat()
            if isinstance(o, Link):
                return dataclass_as_dict(o)
            return json.JSONEncoder.default(self, o)

    with open(join(root_path, "data.json"), "w", encoding="utf8") as file:
        data = {
            "categories": categories,
            "links_by_category": links_by_category,
        }
        json.dump(data, file, cls=DateTimeEncoder, ensure_ascii=False)


def build(build_path: str = join(dirname(realpath(__file__)), "docs/")):
    jinja = Environment(
        loader=FileSystemLoader("templates/"),
        autoescape=select_autoescape(["html", "xml"]),
    )

    with NamedTemporaryFile(suffix=".xlsx") as spreadsheet_file:
        with urllib.request.urlopen(cast(str, ENV["SPREADSHEET_URL"])) as remote_file:
            spreadsheet_file.write(remote_file.read())
            workbook = load_workbook(filename=spreadsheet_file.name, read_only=True)
    links_page_lines = get_rows(
        workbook[cast(str, ENV.get("SPREADSHEET_LINKS_PAGE_NAME", "Links"))]
    )

    logger.info("Validating Workbook")
    required_column_indexes = {
        get_column_index(required_column): required_column
        for required_column in REQUIRED_COLUMNS
    }
    for row in links_page_lines:
        for index, column in enumerate(row):
            if index == 0:
                continue
            if index in required_column_indexes.keys() and column is None:
                print(row)
                raise ValueError(
                    "Line %s - has missing value on column %s."
                    % (row[0] + 1, required_column_indexes[index]))
            if type(column) is str and (column.startswith(" ") or column.endswith(" ")):
                raise ValueError(
                    "Line %s - has a value that must be trimmed on column %s."
                    % (row[0] + 1, required_column_indexes[index]))

    categories_page_lines = get_rows(
        workbook[cast(str, ENV.get("SPREADSHEET_CATEGORIES_PAGE_NAME", "Categories"))]
    )

    category_template = jinja.get_template("category.html.jinja2")
    link_template = jinja.get_template("link.html.jinja2")
    home_template = jinja.get_template("home.html.jinja2")
    sitemap_template = jinja.get_template("sitemap.xml.jinja2")

    links_by_category = get_links_by_category(links_page_lines)
    categories = get_categories(links_page_lines, categories_page_lines)

    category_ids = [r[get_column_index("category_id")] for r in links_page_lines]
    create_category_paths(build_path, category_ids)
    render_json(build_path, categories, links_by_category)
    build_assets(build_path, "./assets/")
    render_categories(build_path, links_by_category, categories, category_template)
    render_links(build_path, links_by_category, categories, link_template)
    render_home(build_path, links_page_lines, categories, home_template)
    render_sitemap(build_path, categories, links_by_category, sitemap_template)
    render_feed(build_path, links_page_lines)


if __name__ == "__main__":
    build()
