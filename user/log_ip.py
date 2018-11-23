
class LogIPMiddleware(object):
    def get_request_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def process_request(self, request):
        user = request.user
        request_ip = self.get_request_ip(request)
        if user and user.is_authenticated() and user.last_ip != request_ip:
            user.last_ip = request_ip
            user.save()
