from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework import status
from .models import User
from .serializers import UserSerializer

class AuthenticateUser(APIView):
    def post(self):
        pass

    def get(self, request):
        return Response({"message": "Hello World"})
    
    def put(self):
        pass