from rest_framework import renderers
import json


class CustomJSONRenderer(renderers.JSONRenderer):
    charset = "UTF-8"

    def render(self, data, accepted_media_type=None, renderer_context=None):
        print("IN RENDERERS -> ", data)
        # Check if data is None, which can happen on some responses
        if data is None:
            return json.dumps({"message": "No data available"}).encode(self.charset)

        # Check if there's an error in the data
        message = data.get("message")
        if isinstance(message, dict) and "detail" in message:
            data["message"] = message["detail"]

        response = data

        # Serialize the response to JSON and encode it with UTF-8
        return json.dumps(response).encode(self.charset)
