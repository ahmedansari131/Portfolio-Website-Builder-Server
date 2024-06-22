from django.utils.functional import SimpleLazyObject
from django.contrib.auth.middleware import get_user
from .utils import verify_simple_jwt


def get_user_jwt(request):
    user = get_user(request)
    print("User ->", user)
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
        # Retrieve the cookie value
        access_token = request.COOKIES.get("access")

        if not access_token:
            request.user = None
            return "Token is not provided"

        try:
            verified_token = verify_simple_jwt(token=access_token)
            request.user = {"email": verified_token.get("email"), "username": verified_token.get("username")}
        except Exception as error:
            return str(error)

        # if access_token:
        #     request.auth_token = auth_token
        # else:
        #     request.auth_token = None
        #     # Optionally, handle the missing auth_token case here

        response = self.get_response(request)
        return response
