# Element Custom Attributes and Values
ELEMENT_DEFAULT_CLASS_NAME = "brand-me"
ASSET_ID_PREFIX = "data-assest-id"
ASSET_ID_VALUE = "asset"
ELEMENT_IDENTIFIER_PREFIX = "data-element-id"
ELEMENT_IDENTIFIER_VALUE = "element"
ELEMENT_TYPE = "data-element-type"
ELEMENT_SUB_TYPE = "data-element-sub-type"
UPLOADABLE_ELEMENT = "uploadable"


DOCUMENT_META_ELEMENTS = ["meta", "link", "script", "title", "style"]

# S3 Template Folders
S3_ASSETS_FOLDER_NAME = "assets"
S3_CSS_FOLDER_NAME = "css"
S3_JS_FOLDER_NAME = "js"

# S3 Template Files
INDEX_FILE = "index.html"
ROOT_STYLE_FILE = "style.css"
UNIVERSAL_STYLE_FILE = "universal-style.css"
RESPONSIVE_STYLE_FILE = "responsive.css"
ROOT_JS_FILE = "script.js"
EMAIL_JS_FILE = "email.js"
TEMPLATE_PREVIEW_IMAGE = "preview.png"


# HTML Element Types
ELEMENT_CATEGORY = {
    "HEADING": {
        "type": "heading",
        "sub_type": "text",
        "tag": ["h1", "h2", "h3", "h4", "h5", "h6"],
    },
    "PARAGRAPH": {"type": "paragraph", "sub_type": "text", "tag": "p"},
    "LINK": {"type": "link", "sub_type": "text", "tag": "a"},
    "BUTTON": {"type": "button", "sub_type": "text", "tag": "button"},
    "SECTION": {"type": "section", "sub_type": "", "tag": "section"},
    "CONTAINER": {"type": "container", "sub_type": "", "tag": "div"},
    "NAV": {"type": "container", "sub_type": "", "tag": "nav"},
    "IMAGE": {"type": "uploadable", "sub_type": "", "tag": "img"},
    "VIDEO": {"type": "video", "sub_type": "", "tag": "video"},
    "INPUT": {"type": "input", "sub_type": "", "tag": "input"},
    "TEXTAREA": {"type": "textarea", "sub_type": "", "tag": "textarea"},
    "LABEL": {"type": "label", "sub_type": "text", "tag": "label"},
    "LIST": {"type": "container", "sub_type": "", "tag": "li"},
    "ICON": {"type": "icon", "sub_type": "", "tag": "i"},
    "FORM": {"type": "container", "sub_type": "", "tag": "form"},
    "UNORDERED_LIST": {"type": "container", "sub_type": "", "tag": "ul"},
    "ORDERED_LIST": {"type": "container", "sub_type": "", "tag": "ol"},
    "SPAN": {"type": "container", "sub_type": "", "tag": "span"},
}
