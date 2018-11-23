from distutils.version import StrictVersion
from django import get_version
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django.utils.timezone import now
from django.db import models
from django.core.exceptions import ImproperlyConfigured
from django.utils.six import text_type
from .utils import id2slug

from .signals import notify

from model_utils import Choices
from jsonfield.fields import JSONField

from django.contrib.auth.models import Group
from common.structures import ChoiceEnum

if StrictVersion(get_version()) >= StrictVersion('1.8.0'):
    from django.contrib.contenttypes.fields import GenericForeignKey
else:
    from django.contrib.contenttypes.generic import GenericForeignKey


# SOFT_DELETE = getattr(settings, 'NOTIFICATIONS_SOFT_DELETE', False)
def is_soft_delete():
    # TODO: SOFT_DELETE = getattr(settings, ...) doesn't work with "override_settings" decorator in unittest
    #     But is_soft_delete is neither a very elegant way. Should try to find better approach
    return getattr(settings, 'NOTIFICATIONS_SOFT_DELETE', False)


def assert_soft_delete():
    if not is_soft_delete():
        msg = """To use 'deleted' field, please set 'NOTIFICATIONS_SOFT_DELETE'=True in settings.
        Otherwise NotificationQuerySet.unread and NotificationQuerySet.read do NOT filter by 'deleted' field.
        """
        raise ImproperlyConfigured(msg)


class NotificationQuerySet(models.query.QuerySet):

    def unread(self):
        """Return only unread items in the current queryset"""
        if is_soft_delete():
            return self.filter(unread=True, deleted=False)
        else:
            """ when SOFT_DELETE=False, developers are supposed NOT to touch 'deleted' field.
            In this case, to improve query performance, don't filter by 'deleted' field
            """
            return self.filter(unread=True)

    def read(self):
        """Return only read items in the current queryset"""
        if is_soft_delete():
            return self.filter(unread=False, deleted=False)
        else:
            """ when SOFT_DELETE=False, developers are supposed NOT to touch 'deleted' field.
            In this case, to improve query performance, don't filter by 'deleted' field
            """
            return self.filter(unread=False)

    def mark_all_as_read(self, recipient=None):
        """Mark as read any unread messages in the current queryset.

        Optionally, filter these by recipient first.
        """
        # We want to filter out read ones, as later we will store
        # the time they were marked as read.
        qs = self.unread()
        if recipient:
            qs = qs.filter(recipient=recipient)

        qs.update(unread=False)

    def mark_all_as_unread(self, recipient=None):
        """Mark as unread any read messages in the current queryset.

        Optionally, filter these by recipient first.
        """
        qs = self.read()

        if recipient:
            qs = qs.filter(recipient=recipient)

        qs.update(unread=True)

    def deleted(self):
        """Return only deleted items in the current queryset"""
        assert_soft_delete()
        return self.filter(deleted=True)

    def active(self):
        """Return only active(un-deleted) items in the current queryset"""
        assert_soft_delete()
        return self.filter(deleted=False)

    def mark_all_as_deleted(self, recipient=None):
        """Mark current queryset as deleted.
        Optionally, filter by recipient first.
        """
        assert_soft_delete()
        qs = self.active()
        if recipient:
            qs = qs.filter(recipient=recipient)

        qs.update(deleted=True)

    def mark_all_as_active(self, recipient=None):
        """Mark current queryset as active(un-deleted).
        Optionally, filter by recipient first.
        """
        assert_soft_delete()
        qs = self.deleted()
        if recipient:
            qs = qs.filter(recipient=recipient)

        qs.update(deleted=False)


class Notification(models.Model):
    """
    Action model describing the actor acting out a verb (on an optional
    target).
    Nomenclature based on http://activitystrea.ms/specs/atom/1.0/

    Generalized Format::

        <actor> <verb> <time>
        <actor> <verb> <target> <time>
        <actor> <verb> <action_object> <target> <time>

    Examples::

        <justquick> <reached level 60> <1 minute ago>
        <brosner> <commented on> <pinax/pinax> <2 hours ago>
        <washingtontimes> <started follow> <justquick> <8 minutes ago>
        <mitsuhiko> <closed> <issue 70> on <mitsuhiko/flask> <about 2 hours ago>

    Unicode Representation::

        justquick reached level 60 1 minute ago
        mitsuhiko closed issue 70 on mitsuhiko/flask 3 hours ago

    HTML Representation::

        <a href="http://oebfare.com/">brosner</a> commented on <a href="http://github.com/pinax/pinax">pinax/pinax</a> 2 hours ago

    """
    LEVELS = Choices('success', 'info', 'warning', 'error')
    level = models.CharField(choices=LEVELS, default=LEVELS.info, max_length=20)

    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, blank=False, related_name='notifications')
    unread = models.BooleanField(default=True, blank=False)

    actor_content_type = models.ForeignKey(ContentType, related_name='notify_actor')
    actor_object_id = models.PositiveIntegerField()
    actor = GenericForeignKey('actor_content_type', 'actor_object_id')

    verb = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    target_content_type = models.ForeignKey(ContentType, related_name='notify_target', blank=True, null=True)
    target_object_id = models.PositiveIntegerField(blank=True, null=True)
    target = GenericForeignKey('target_content_type', 'target_object_id')

    action_object_content_type = models.ForeignKey(ContentType, blank=True, null=True,
                                                   related_name='notify_action_object')
    action_object_object_id = models.PositiveIntegerField(blank=True, null=True)
    action_object = GenericForeignKey('action_object_content_type', 'action_object_object_id')

    timestamp = models.DateTimeField(default=timezone.now)

    public = models.BooleanField(default=True)
    deleted = models.BooleanField(default=False)
    emailed = models.BooleanField(default=False)

    data = JSONField(blank=True, null=True)
    objects = NotificationQuerySet.as_manager()

    class Meta:
        ordering = ('-timestamp', )
        app_label = 'notifications'

    def __unicode__(self):
        ctx = {
            'actor': self.actor,
            'verb': self.verb,
            'action_object': self.action_object,
            'target': self.target,
            'timesince': self.timesince()
        }
        if self.target:
            if self.action_object:
                return u'%(actor)s %(verb)s %(action_object)s on %(target)s %(timesince)s ago' % ctx
            return u'%(actor)s %(verb)s %(target)s %(timesince)s ago' % ctx
        if self.action_object:
            return u'%(actor)s %(verb)s %(action_object)s %(timesince)s ago' % ctx
        return u'%(actor)s %(verb)s %(timesince)s ago' % ctx

    def __str__(self):  # Adds support for Python 3
        return self.__unicode__()

    def timesince(self, now=None):
        """
        Shortcut for the ``django.utils.timesince.timesince`` function of the
        current timestamp.
        """
        from django.utils.timesince import timesince as timesince_
        return timesince_(self.timestamp, now)

    @property
    def slug(self):
        return id2slug(self.id)

    def mark_as_read(self):
        if self.unread:
            self.unread = False
            self.save()

    def mark_as_unread(self):
        if not self.unread:
            self.unread = True
            self.save()

# 'NOTIFY_USE_JSONFIELD' is for backward compatibility
# As app name is 'notifications', let's use 'NOTIFICATIONS' consistently from now
EXTRA_DATA = getattr(settings, 'NOTIFY_USE_JSONFIELD', None)
if EXTRA_DATA is None:
    EXTRA_DATA = getattr(settings, 'NOTIFICATIONS_USE_JSONFIELD', False)


def notify_handler(verb, actor, recipient, public,  description, timestamp,
                   level, target=None, action_object=None, **extra_data):
    """
    Handler function to create Notification instance upon action signal call.
    """

    # Check if User or Group
    if isinstance(recipient, Group):
        recipients = recipient.user_set.all()
    elif isinstance(recipient, (list, tuple)):
        recipients = recipient
    else:
        recipients = [recipient]

    for recipient in recipients:
        notification = Notification(
            recipient=recipient,
            actor=actor,
            verb=text_type(verb),
            public=public,
            description=description,
            timestamp=timestamp,
            level=level,
            target=target,
            action_object=action_object,
        )

        if len(extra_data) and EXTRA_DATA:
            notification.data = extra_data

        notification.save()


class Notify(ChoiceEnum):
    SYSTEM_LOGIN = 'logged in',
    SYSTEM_LOGOUT = 'logged out',

    ADVISOR_INVITE_NEW_CLIENT = 'invited a new client'
    ADVISOR_RESEND_INVITE = 'resent invite'

    ADVISOR_CREATE_GROUP = 'created group'
    ADVISOR_REMOVE_GROUP = 'removed group'
    ADVISOR_CLIENT_AGREEMENT_DOWNLOAD = "downloaded client's agreement"

    ADVISOR_ADD_SECONDARY_ADVISOR = 'added secondary advisor'
    ADVISOR_REMOVE_SECONDARY_ADVISOR = 'removed secondary advisor'

    SUBMIT_FORM = 'submitted new form'
    UPDATE_FORM = 'updated form'

    CREATE_SUPERVISOR = 'created supervisor'

    UPDATE_PERSONAL_INFO = 'updated personal info'

    CLIENT_AGREE_RETIREMENT_PLAN = 'agreed'

    ADVISOR_CREATE_ROA = 'created'

    def send(self, actor, target=None, recipient=None, action_object=None,
             public=True, description=None, timestamp=None,
             level=Notification.LEVELS.info):

        if recipient is None:
            try:
                recipient = actor.user
            except AttributeError:
                recipient = actor

        if timestamp is None:
            timestamp = now()

        notify_handler(self.value, actor, recipient, public, description,
                       timestamp, level, target, action_object)


# connect the signal
notify.connect(notify_handler, dispatch_uid='notifications.models.notification')
