from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import UntypedToken


class CookieJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        access_token = request.COOKIES.get("access")
        if access_token is None:
            raise AuthenticationFailed("Please sign in to proceed further.")

        try:
            decoded_token = UntypedToken(access_token).payload  # Verifies the token
        except Exception as e:
            raise AuthenticationFailed(f"Invalid token: {str(e)}")

        # If token is valid, authenticate the user
        user = self.get_user(decoded_token)
        return user, access_token

    def get_user(self, token):
        # This method can be used to retrieve the user based on the token
        return super().get_user(token)
