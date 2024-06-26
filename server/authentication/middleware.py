from django.utils.functional import SimpleLazyObject
from django.contrib.auth.middleware import get_user
from .utils import verify_simple_jwt


def get_user_jwt(request):
    user = get_user(request)
    return user


class JWTAuthenticationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.user = SimpleLazyObject(lambda: get_user_jwt(request))
        return self.get_response(request)


class CookieMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        access_token = request.COOKIES.get("access")

        if access_token:
            try:
                verified_token = verify_simple_jwt(token=access_token)
                request.user = {
                    "email": verified_token.get("email"),
                    "username": verified_token.get("username"),
                }
            except Exception as error:
                print("error ->", error)
                raise error

        response = self.get_response(request)
        return response


class LogIPAddressAndUserAgentMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.ip_address = self.get_ip_address(request)
        request.user_agent = request.META.get("HTTP_USER_AGENT", "")
        response = self.get_response(request)
        return response

    def get_ip_address(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip
