from .element_attr import assign_asset_id, assign_identifier, assign_class_name
from portfolio.constants import DOCUMENT_META_ELEMENTS
from bs4 import BeautifulSoup


def extract_element(dom, tag_name):
    tag = dom.find_all(tag_name)
    if tag:
        return tag
    else:
        return ""


def build_dom_tree(elem, is_template=None):
    if not elem:
        return None

    if not is_template:
        if not elem.name in DOCUMENT_META_ELEMENTS:
            elem = assign_class_name(elem=elem)
            elem = assign_identifier(elem=elem)

            # add asset id to image
            if elem.name == "img":
                elem = assign_asset_id(elem=elem)

    dom_tree = {
        "tag": elem.name,
        "attributes": elem.attrs if elem.attrs else {},
        "text": elem.string.strip() if elem.string else "",
        "children": [],
    }

    for child in elem.contents:
        if isinstance(child, str):
            if dom_tree["text"] == "":
                dom_tree["text"] += child.strip()
        elif child.name is not None:
            dom_tree["children"].append(build_dom_tree(child))
    return dom_tree


def parse_html_content(index_response, css_response, js_response):
    html_content = index_response["Body"].read().decode("utf-8")
    css = [obj["Key"] for obj in css_response.get("Contents", [])]
    js = [obj["Key"] for obj in js_response.get("Contents", [])]

    soup = BeautifulSoup(html_content, "html.parser")
    tags = ["meta", "link", "title", "style", "body", "script"]
    dom_tree_json = {}

    for tag in tags:
        elements = extract_element(soup, tag)
        if elements:
            if tag not in dom_tree_json:
                dom_tree_json[tag] = []
            for element in elements:
                dom_tree_json[tag].append(build_dom_tree(element))

    # Extracting anchor and image tags for further processing on it
    img_tags = soup.find_all("img")
    anchor_tags = soup.find_all("a")

    return (
        dom_tree_json,
        css,
        js,
        img_tags,
        anchor_tags,
    )

