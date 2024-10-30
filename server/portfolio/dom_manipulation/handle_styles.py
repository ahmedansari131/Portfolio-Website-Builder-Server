import os
from portfolio.constants import (
    S3_CSS_FOLDER_NAME,
    ROOT_STYLE_FILE,
    UNIVERSAL_STYLE_FILE,
    INDEX_FILE,
)
import re
from portfolio.exceptions.exceptions import GeneralError, DataNotPresent
from bs4 import BeautifulSoup


def append_universal_style_link(index_file_path, style_path):
    # Read the index file content
    try:
        with open(index_file_path, "r") as index_file:
            html_content = index_file.read()
    except Exception as error:
        print("Error occurred while reading the index file -> ", error)
        raise GeneralError("Error occurred while processing the html file")

    # Parse the HTML content
    soup = BeautifulSoup(html_content, "html.parser")

    # Create a new <link> tag for the stylesheet
    new_tag = soup.new_tag("link", rel="stylesheet", href=style_path)

    # Append the new tag to the <head> section
    head = soup.head
    if head is not None:
        head.append(new_tag)
    else:
        print("No <head> tag found in the HTML document.")

    try:
        # Write the modified content back to the index file
        with open(index_file_path, "w") as index_file:
            index_file.write(str(soup))
    except Exception as error:
        print(
            "Error occurred while writing universal css link into index file -> ", error
        )
        raise GeneralError("Error occurred while processing the html file")
    return


def create_separate_universal_style(template_path):
    # Read the existing CSS file
    template_style_path = os.path.join(
        template_path, S3_CSS_FOLDER_NAME, ROOT_STYLE_FILE
    )

    try:
        with open(template_style_path, "r") as file:
            css_content = file.read()
    except FileNotFoundError:
        print(f"{template_style_path} -> This path does not exist")
        raise DataNotPresent(f"{template_style_path} -> Does not exist")
    except Exception as error:
        print("Error occurred while processing the template styles -> ", error)
        raise GeneralError(f"Error occrurred while processing the template styles")

    # Extract body styles using regex
    universal_styles = re.findall(r"\*\s*{(.*?)\}", css_content, re.DOTALL)  # *{}
    body_styles = re.findall(r"body\s*{(.*?)\}", css_content, re.DOTALL)  # body{}

    # Create a new CSS file for body styles
    output_body_file_name = UNIVERSAL_STYLE_FILE
    output_body_style_path = os.path.join(
        template_path, S3_CSS_FOLDER_NAME, output_body_file_name
    )

    if body_styles:
        with open(output_body_style_path, "w") as body_file:
            # Write universal styles if found
            if universal_styles:
                body_file.write(f"* {{\n{universal_styles[0].strip()}\n}}\n\n")

            # Write body styles if found
            if body_styles:
                body_file.write(f"body {{\n{body_styles[0].strip()}\n}}")

    # Remove the extracted styles from the original CSS content
    updated_css_content = css_content
    if universal_styles:
        updated_css_content = re.sub(
            r"\*\s*{.*?}\s*", "", updated_css_content, flags=re.DOTALL
        )

    if body_styles:
        updated_css_content = re.sub(
            r"body\s*{.*?}\s*", "", updated_css_content, flags=re.DOTALL
        )

    try:
        # Write the updated CSS back to style.css
        with open(template_style_path, "w") as file:
            file.write(updated_css_content)
    except Exception as error:
        print("Error occurred while processing the template styles -> ", error)
        raise GeneralError("Error occurred while processing the template styles")

    index_file_path = os.path.join(template_path, INDEX_FILE)
    style_path = f"{S3_CSS_FOLDER_NAME}/{output_body_file_name}"
    append_universal_style_link(index_file_path, style_path)
    return
