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
