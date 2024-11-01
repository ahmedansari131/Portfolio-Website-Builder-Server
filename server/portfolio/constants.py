# Element Custom Attributes and Values
ELEMENT_DEFAULT_CLASS_NAME = "brand-me"
ASSET_ID_PREFIX = "data-assest-id"
ASSET_ID_VALUE = "asset"
ELEMENT_IDENTIFIER_PREFIX = "data-element-id"
ELEMENT_IDENTIFIER_VALUE = "element"
ELEMENT_TYPE = 'data-element-type'


DOCUMENT_META_ELEMENTS = ["meta", "link", "script", "title", "style"]

# S3 Template Folders
S3_ASSETS_FOLDER_NAME = "assets"
S3_CSS_FOLDER_NAME = "css"
S3_JS_FOLDER_NAME = "js"

# S3 Template Files
INDEX_FILE = "index.html"
ROOT_STYLE_FILE = "style.css"
UNIVERSAL_STYLE_FILE = "universal-style.css"
ROOT_JS_FILE = "script.js"
EMAIL_JS_FILE = "email.js"
TEMPLATE_PREVIEW_IMAGE = "preview.png"


# HTML Element Types
ELEMENT_CATEGORY = {
    "HEADING": {"type": "heading", "tag": ["h1", "h2", "h3", "h4", "h5", "h6"]},
    "PARAGRAPH": {"type": "paragraph", "tag": "p"},
    "LINK": {"type": "link", "tag": "a"},
    "BUTTON": {"type": "button", "tag": "button"},
    "SECTION": {"type": "section", "tag": "section"},
    "CONTAINER": {"type": "container", "tag": "div"},
    "NAV": {"type": "container", "tag": "nav"},
    "IMAGE": {"type": "uploadable", "tag": "img"},
    "VIDEO": {"type": "video", "tag": "video"},
    "INPUT": {"type": "input", "tag": "input"},
    "TEXTAREA": {"type": "textarea", "tag": "textarea"},
    "LABEL": {"type": "label", "tag": "label"},
    "LIST": {"type": "list", "tag": "li"},
    "ICON": {"type": "icon", "tag": "i"},
    "FORM": {"type": "container", "tag": "form"},
    "UNORDERED_LIST": {"type": "container", "tag": "ul"},
    "ORDERED_LIST": {"type": "container", "tag": "ol"},
    "SPAN": {"type": "container", "tag": "span"},
}
