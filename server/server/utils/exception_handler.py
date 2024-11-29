from rest_framework.views import exception_handler
from server.response.api_response import ApiResponse
from rest_framework import exceptions


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        if isinstance(exc, exceptions.NotAuthenticated):
            return ApiResponse.response_failed(
                message="You are not signed in. Please sign in to proceed further!",
                status=401,
            )
        elif isinstance(exc, exceptions.PermissionDenied):
            return ApiResponse.response_failed(
                message="You do not have permission to perform this action.", status=403
            )
        return ApiResponse.response_failed(
            status=response.status_code, message=response.data
        )
    return response
