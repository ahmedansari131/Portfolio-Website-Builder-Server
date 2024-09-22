from django.utils.functional import SimpleLazyObject
from django.contrib.auth.middleware import get_user
from .utils import verify_simple_jwt
from rest_framework_simplejwt.tokens import UntypedToken


def get_user_jwt(request):
    user = get_user(request)
    return user


class JWTAndCookieAuthenticationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        access_token = request.COOKIES.get("access")
        if access_token:
            try:
                UntypedToken(access_token)  # Verifies the token
                request.user = SimpleLazyObject(lambda: get_user_jwt(request))
            except Exception as error:
                print("error ->", error)
                request.user = SimpleLazyObject(lambda: None)
        else:
            request.user = SimpleLazyObject(lambda: get_user_jwt(request))
        
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
