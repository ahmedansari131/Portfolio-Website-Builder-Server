from bs4 import BeautifulSoup
from portfolio.dom_manipulation.element_attr import assign_asset_id
from portfolio.constants import (
    S3_ASSETS_FOLDER_NAME,
    ASSET_ID_PREFIX,
    DOCUMENT_META_ELEMENTS,
    INDEX_FILE,
    ELEMENT_DEFAULT_CLASS_NAME,
    ELEMENT_IDENTIFIER_PREFIX,
    ELEMENT_IDENTIFIER_VALUE,
)
import os
from server.utils.s3 import AWS_S3_Operations, get_cloudfront_domain, download_assets
from django.conf import settings
from portfolio.exceptions.exceptions import GeneralError
from portfolio.utils import generate_random_characters

empty_html_template = """
                        <!DOCTYPE html>
                        <html lang="en">
                        <head>
                            <meta charset="UTF-8">
                            <meta name="viewport" content="width=device-width, initial-scale=1.0">
                            <title></title>
                        </head>
                        <body>
                        </body>
                        </html>
                    """


def extract_element(dom, tag_name):
    tag = dom.find_all(tag_name)
    if tag:
        return tag
    else:
        return ""


class HTML_Document:
    def __init__(self):
        self.inital_html = empty_html_template
        self.soup = BeautifulSoup(self.inital_html, "html.parser")

    def update_head_content(self, element_json=[]):
        head_tag = self.soup.head
        for element in element_json:
            tag = self.soup.new_tag(element["tag"])
            if element["tag"] == "title":
                title_tag = self.soup.title

                if not title_tag.get_text():
                    tag.string = element["text"]
                    title_tag.replace_with(tag)
                    return

            for attr, value in element["attributes"].items():
                tag[attr] = " ".join(value) if isinstance(value, list) else value

            head_tag.append(tag)

        return

    def update_body_content(self, body_json=[]):
        body_tag = self.soup.body
        parsed_body = self.parse_body_element(body_json)[0]
        body_tag.replace_with(parsed_body)

        return

    def parse_body_element(self, elements, parent=None):
        top_level_elements = []
        for element in elements:
            tag_name = element.get("tag").lower()
            new_tag = self.soup.new_tag(tag_name)

            if "attributes" in element and len(element.get("attributes")):
                for attr, value in element.get("attributes").items():
                    if isinstance(value, list):
                        new_tag[attr] = " ".join(value)  # Join classes with space
                    else:
                        new_tag[attr] = value
            if "text" in element and element.get("text"):
                new_tag.string = element.get("text")

            if "children" in element and element.get("children"):
                self.parse_body_element(element.get("children"), new_tag)

            if parent:
                parent.append(new_tag)
            else:
                top_level_elements.append(new_tag)

        if parent is None:
            return top_level_elements

        return parent

    def add_script_to_body(self, scripts_json=[]):
        body_tag = self.soup.body

        for script in scripts_json:
            script_tag = self.soup.new_tag("script")

            for key, value in script["attributes"].items():
                script_tag[key] = value

            body_tag.append(script_tag)

        return


def handle_anchor_element(anchor_tag, template_name):
    if anchor_tag:
        # If download attribute is present in anchor, then it is asset
        if anchor_tag.get("download"):
            href = anchor_tag.get("href")
            anchor_tag = assign_asset_id(anchor_tag)
            asset_name = anchor_tag.get(ASSET_ID_PREFIX)
            old_s3_asset_key = (
                f'{template_name}/{S3_ASSETS_FOLDER_NAME}/{href.split("/")[-1]}'
            )
            new_s3_asset_key = f"{template_name}/{S3_ASSETS_FOLDER_NAME}/{asset_name}"
            bucket_name = settings.AWS_STORAGE_TEMPLATE_BUCKET_NAME

            # Renaming the asset file
            AWS_S3_Operations.copy_object_in_s3(
                old_s3_asset_key=old_s3_asset_key,
                new_s3_asset_key=new_s3_asset_key,
                bucket_name=bucket_name,
            )

            # Deleting the old asset file
            AWS_S3_Operations.delete_object_in_s3(
                bucket_name=bucket_name, old_s3_asset_key=old_s3_asset_key
            )

            domain_name = os.environ.get("DOMAIN_NAME")
            template_cloudfront_domain = get_cloudfront_domain(
                distribution_id=os.environ.get(
                    "PREBUILT_TEMPLATES_CLOUDFRONT_DISTRIBUION_ID"
                )
            )

            if domain_name:
                anchor_path = f"{S3_ASSETS_FOLDER_NAME}/{asset_name}"
            else:
                anchor_path = f"https://{template_cloudfront_domain}/{template_name}/{S3_ASSETS_FOLDER_NAME}/{asset_name}"

            anchor_tag["href"] = anchor_path
    return anchor_tag


def handle_image_source(img_tag, template_name):
    if img_tag:
        src = img_tag.get("src")
        asset_name = img_tag.get(ASSET_ID_PREFIX)
        bucket_name = settings.AWS_STORAGE_TEMPLATE_BUCKET_NAME

        # If image is coming from some online sources -> copying to the s3
        if "https" in src:
            dowloaded_asset = download_assets(
                asset_url=src,
                asset_name=asset_name,
                s3_template_name=template_name,
            )

        # If image is stored in local -> copying to the s3
        elif not "https" in src and not "http" in src:
            old_s3_key = f'{template_name}/{S3_ASSETS_FOLDER_NAME}/{src.split("/")[-1]}'
            new_s3_key = f"{template_name}/{S3_ASSETS_FOLDER_NAME}/{asset_name}"

            AWS_S3_Operations.copy_object_in_s3(
                bucket_name=bucket_name,
                new_s3_asset_key=new_s3_key,
                old_s3_asset_key=old_s3_key,
            )

            AWS_S3_Operations.delete_object_in_s3(
                bucket_name=bucket_name, old_s3_asset_key=old_s3_key
            )

        image_path = ""
        domain_name = os.environ.get("DOMAIN_NAME")
        template_cloudfront_domain = get_cloudfront_domain(
            distribution_id=os.environ.get(
                "PREBUILT_TEMPLATES_CLOUDFRONT_DISTRIBUION_ID"
            )
        )

        if domain_name:
            image_path = f"{S3_ASSETS_FOLDER_NAME}/{asset_name}"
        else:
            image_path = f"https://{template_cloudfront_domain}/{template_name}/{S3_ASSETS_FOLDER_NAME}/{asset_name}"
        img_tag["src"] = image_path

    return img_tag


def build_dom_tree(elem, template_name):
    if not elem:
        return None

    if not elem.name in DOCUMENT_META_ELEMENTS:
        # add asset id to image and update the src
        if elem.name == "img":
            elem = assign_asset_id(elem=elem)
            elem = handle_image_source(img_tag=elem, template_name=template_name)

        # add asset id to image and update the href
        if elem.name == "a" and elem.get("download"):
            elem = assign_asset_id(elem=elem)
            elem = handle_anchor_element(
                anchor_tag=elem,
                template_name=template_name,
            )

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
            dom_tree["children"].append(build_dom_tree(child, template_name))
    return dom_tree


def parse_html_content(html_content, template_name):
    soup = BeautifulSoup(html_content, "html.parser")
    tags = ["meta", "link", "title", "style", "body", "script"]
    dom_tree_json = {}

    for tag in tags:
        elements = extract_element(soup, tag)
        if elements:
            if tag not in dom_tree_json:
                dom_tree_json[tag] = []
            for element in elements:
                dom_tree_json[tag].append(build_dom_tree(element, template_name))

    return dom_tree_json


def build_html_using_json(template_name):
    parsed_content = parse_local_index_file(template_name)
    meta = parsed_content.get("meta", [])
    link = parsed_content.get("link", [])
    body = parsed_content.get("body", [])
    script = parsed_content.get("script", [])
    title = parsed_content.get("title", [])

    document = HTML_Document()
    document.update_head_content(meta)
    document.update_head_content(title)
    document.update_head_content(link)
    document.update_body_content(body)
    document.add_script_to_body(script)

    return {"html": document.soup, "html_json": parsed_content}


def parse_local_index_file(template_name):
    local_index_file_path = os.path.join(
        settings.TEMPLATES_BASE_DIR, template_name, INDEX_FILE
    )

    try:
        with open(local_index_file_path, "r") as html_index_file:
            dom_json_response = parse_html_content(
                html_index_file, template_name=template_name
            )

        if dom_json_response:
            return dom_json_response
    except Exception as error:
        print("Error occurred while reading the html file on local -> ", error)
        raise GeneralError("Error occurred while reading the html file on local")


def parse_dom_tree(dom_tree):
    if not dom_tree:
        raise GeneralError("DOM tree is not provided.")

    # Assign classname and unique identifier
    class_name = (
        f"{ELEMENT_DEFAULT_CLASS_NAME}-{generate_random_characters(digits=8)}".lower()
    )
    unique_identifier = (
        f"{ELEMENT_IDENTIFIER_VALUE}-{generate_random_characters(digits=8)}".lower()
    )

    if not dom_tree["tag"] == "body":
        if "class" in dom_tree["attributes"]:
            dom_tree["attributes"]["class"].append(class_name)
        else:
            dom_tree["attributes"]["class"] = [class_name]

        dom_tree["attributes"][ELEMENT_IDENTIFIER_PREFIX] = unique_identifier

    for child in dom_tree["children"]:
        parse_dom_tree(dom_tree=child)

    return dom_tree
