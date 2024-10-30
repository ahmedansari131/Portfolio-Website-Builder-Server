from portfolio.utils import generate_random_characters
from portfolio.constants import (
    ELEMENT_DEFAULT_CLASS_NAME,
    ASSET_ID_VALUE,
    ASSET_ID_PREFIX,
    ELEMENT_IDENTIFIER_PREFIX,
    ELEMENT_IDENTIFIER_VALUE,
)


def assign_class_name(elem):
    if elem:
        created_class_name = f"{ELEMENT_DEFAULT_CLASS_NAME}-{generate_random_characters(digits=8)}".lower()

        # Check if the element has a "class" attribute
        if elem.has_attr("class"):
            # Append the new class to the list of existing classes
            elem["class"].append(created_class_name)
        else:
            # Set a new class if none exists
            elem["class"] = [created_class_name]
        return elem


def assign_asset_id(elem):
    if elem:
        created_asset_id = (
            f"{ASSET_ID_VALUE}-{generate_random_characters(digits=8)}".lower()
        )

        elem[ASSET_ID_PREFIX] = created_asset_id
        return elem


def assign_identifier(elem):
    if elem:
        created_element_identifier = (
            f"{ELEMENT_IDENTIFIER_VALUE}-{generate_random_characters(digits=8)}".lower()
        )

        elem[ELEMENT_IDENTIFIER_PREFIX] = created_element_identifier
        return elem
