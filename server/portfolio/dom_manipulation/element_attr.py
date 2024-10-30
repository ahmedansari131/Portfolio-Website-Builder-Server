from portfolio.utils import generate_random_characters
from portfolio.constants import (
    ELEMENT_DEFAULT_CLASS_NAME,
    DATA_ASSET_ID_ATTR,
    ELEMENT_IDENTIFIER,
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
            f"{DATA_ASSET_ID_ATTR}-{generate_random_characters(digits=8)}".lower()
        )

        elem[DATA_ASSET_ID_ATTR] = created_asset_id
        return elem


def assign_identifier(elem):
    if elem:
        created_element_identifier = (
            f"{ELEMENT_IDENTIFIER}-{generate_random_characters(digits=8)}".lower()
        )

        elem[ELEMENT_IDENTIFIER] = created_element_identifier
        return elem
