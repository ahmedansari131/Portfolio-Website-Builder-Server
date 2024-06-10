from .models import User


def get_existing_user(user_id):
    try:
        user = User.objects.get(id=user_id)
        return user
    except User.DoesNotExist:
        return "User does not exist"
    except Exception as error:
        return error
