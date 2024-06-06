from rest_framework.response import Response


class ApiResponse:

    @staticmethod
    def response_succeed(status, success=True, message=None, data=None):
        return Response({"success": success, "data": data, "message": message}, status=status)

    @staticmethod
    def response_failed(status, success=False, message=None):
        return Response({"success": success, "message": message}, status=status)
