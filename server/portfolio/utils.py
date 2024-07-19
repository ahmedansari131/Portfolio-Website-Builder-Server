import random
import string


def generate_random_number(digits=6):
    characters = string.ascii_letters + string.digits

    random_string = "".join(random.choice(characters) for _ in range(digits))
    return random_string
