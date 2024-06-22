from django.utils.functional import SimpleLazyObject
from django.contrib.auth.middleware import get_user

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
