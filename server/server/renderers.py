import json
from rest_framework import renderers


class CustomJSONRenderer(renderers.JSONRenderer):
    charset = "UTF-8"

    def render(self, data, accepted_media_type=None, renderer_context=None):
        if "ErrorDetail" in str(data):
            data["message"] = str(data.get("message").get("detail"))
            response = data
            return json.dumps(response)
        else:
            response = data
        return json.dumps(response)
