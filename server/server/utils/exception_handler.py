from rest_framework.views import exception_handler
from server.response.api_response import ApiResponse


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    print("This is response -> ", response.data)

    if response is not None:
        return ApiResponse.response_failed(
            status=response.status_code, message=response.data
        )

    return response
