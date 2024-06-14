class BaseResponse:

    @staticmethod
    def error(message):
        return {"error": True, "message": message}
