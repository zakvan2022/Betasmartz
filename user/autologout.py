from calendar import timegm
from datetime import datetime

from django.contrib import messages
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from django.utils import timezone
from django.conf import settings

__all__ = ['SessionExpire']


class SessionExpire:
    _key_name = '__expire_at'

    def __init__(self, request):
        self.request = request

    def expire_time(self):
        try:
            timestamp = self.request.session[self._key_name]
            return datetime.fromtimestamp(timestamp, timezone.UTC())
        except KeyError:
            pass

    def keep_alive(self):
        now = timegm(timezone.now().utctimetuple())
        self.request.session[self._key_name] = now + self.get_session_length()

    def get_session_length(self):
        user = self.request.user
        if user.is_authenticated():
            if user.is_client:
                return settings.CLIENT_SESSION_TIMEOUT
            return settings.AUTHENTICATED_SESSION_TIMEOUT
        return 300  # 5 min

    def check(self):
        expire_at = self.request.session.get(self._key_name)
        if expire_at:
            now = timegm(timezone.now().utctimetuple())
            if expire_at < now:
                self.request.session.flush()
                self.notify_user_its_expired()
            else:
                self.keep_alive()

    def notify_user_its_expired(self):
        messages.add_message(self.request, messages.WARNING,
                             'You have been logged out due to inactivity '
                             'to prevent unauthorised access.')


class SessionExpireMiddleware:
    def process_request(self, request):
        assert hasattr(request, 'session'), (
            "The Django authentication middleware requires session middleware "
            "to be installed. Edit your MIDDLEWARE_CLASSES setting to insert "
            "'django.contrib.sessions.middleware.SessionMiddleware' before "
            "'django.contrib.auth.middleware.AuthenticationMiddleware'."
        )
        SessionExpire(request).check()


def session_expire_context_processor(request):
    return {
        'session_expires_at': SessionExpire(request).expire_time(),
    }


@receiver(user_logged_in)
def set_session_expiration_time(sender, request, **kwargs):
    SessionExpire(request).keep_alive()
