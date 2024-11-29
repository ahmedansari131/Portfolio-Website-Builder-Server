from rest_framework.exceptions import APIException
from rest_framework import status


class GeneralServiceError(Exception):
    pass


class CustomAPIException(APIException):
    status_code = status.HTTP_400_BAD_REQUEST  # Default to 400 Bad Request
    default_detail = "A server error occurred."
    default_code = "error"

    def __init__(self, detail=None, status_code=None, code=None):
        if detail:
            self.detail = detail
        else:
            self.detail = self.default_detail
        if status_code:
            self.status_code = status_code
        if code:
            self.default_code = code
        super().__init__(self.detail)

    def __str__(self):
        return str(self.detail)

    # You can override the 'get_full_details' method if you want a custom structure
    def get_full_details(self):
        return {
            "success": False,
            "message": str(self.detail),
            "status": self.default_code,
        }
