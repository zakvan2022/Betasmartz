from django.conf import settings
from django.contrib.auth import hashers
from django.contrib.auth.models import AbstractBaseUser, Group, \
    PermissionsMixin, UserManager, send_mail
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.dispatch import receiver
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _
from common.constants import GROUP_SUPPORT_STAFF
from main import constants
from notifications.models import Notify


def groups_add(self, name):
    """
    Custom helper method for User class to add group(s).
    """
    group, _ = Group.objects.get_or_create(name=name)
    group.user_set.add(self)

    return self


def groups_remove(self, name):
    """
    Custom helper method for User class to remove group(s).
    """
    group, _ = Group.objects.get_or_create(name=name)
    group.user_set.remove(self)

    return self


class User(AbstractBaseUser, PermissionsMixin):
    """
    An abstract base class implementing a fully featured User model with
    admin-compliant permissions.

    Username, password and email are required. Other fields are optional.
    """

    first_name = models.CharField(_('first name'), max_length=30)
    middle_name = models.CharField(_('middle name(s)'), max_length=30,
                                   blank=True)
    last_name = models.CharField(_('last name'), max_length=30, db_index=True)
    username = models.CharField(max_length=255, editable=False, default='')
    email = models.EmailField(
        _('email address'),
        unique=True,
        error_messages={
            'unique': _("A user with that email already exists."),
        })

    is_staff = models.BooleanField(
        _('staff status'),
        default=False,
        help_text=_(
            'Designates whether the user can log into this admin site.'))
    is_active = models.BooleanField(
        _('active'),
        default=True,
        help_text=_('Designates whether this user should be treated as '
                    'active. Unselect this instead of deleting accounts.'))

    date_joined = models.DateTimeField(_('date joined'), auto_now_add=True)
    prepopulated = models.BooleanField(default=False)

    avatar = models.ImageField(_('avatar'), blank=True, null=True)

    last_ip = models.CharField(max_length=20, blank=True, null=True,
                               help_text='Last requested IP address')

    # aka activity
    notifications = GenericRelation('notifications.Notification',
                                    related_query_name='users',
                                    content_type_field='actor_content_type_id',
                                    object_id_field='actor_object_id')

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'username']

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')

    @property
    def full_name(self):
        return self.get_full_name()

    @property
    def role(self):
        if self.is_advisor:
            return 'advisor'
        elif self.is_client:
            return 'client'
        elif self.is_supervisor:
            return 'supervisor'
        elif self.is_authorised_representative:
            return 'authorised_representative'
        elif hasattr(self, 'invitation'):
            return 'client'
        elif hasattr(self, 'firm_invitation'):
            return 'authorised_representative'
        else:
            return 'none'

    @cached_property
    def is_advisor(self):
        """
        Custom helper method for User class to check user type/profile.
        """
        if not hasattr(self, '_is_advisor'):
            self._is_advisor = hasattr(self, 'advisor')

        return self._is_advisor

    @cached_property
    def is_authorised_representative(self):
        """
        Custom helper method for User class to check user type/profile.
        """
        if not hasattr(self, '_is_authorised_representative'):
            self._is_authorised_representative = hasattr(self, 'authorised_representative')

        return self._is_authorised_representative

    @cached_property
    def is_client(self):
        """
        Custom helper method for User class to check user type/profile.
        """
        if not hasattr(self, '_is_client'):
            self._is_client = hasattr(self, 'client')
        return self._is_client

    @cached_property
    def is_supervisor(self):
        """
        Custom helper method for User class to check user type/profile.
        """
        if not hasattr(self, '_is_supervisor'):
            self._is_supervisor = hasattr(self, 'supervisor')

        return self._is_supervisor

    @cached_property
    def is_support_staff(self):
        if not hasattr(self, '_is_support_staff'):
            group = Group.objects.get(name=GROUP_SUPPORT_STAFF)
            self._is_support_staff = group in self.groups.all()
        return self._is_support_staff

    def get_full_name(self):
        """
        Returns the first_name plus the last_name, with a space in between.
        """
        full_name = '%s %s' % (self.first_name, self.last_name)
        return full_name.strip()

    def get_short_name(self):
        " Returns the short name for the user."
        return self.first_name

    def email_user(self, subject, message="",
                   from_email=settings.DEFAULT_FROM_EMAIL, **kwargs):
        """
        Sends an email to this User.
        """
        send_mail(subject, message, from_email, [self.email], **kwargs)

    def login_url(self):
        return settings.SITE_URL + "/login"


# Add custom methods to User class
User.add_to_class('groups_add', groups_add)
User.add_to_class('groups_remove', groups_remove)

User.add_to_class('GROUP_ADVISOR', 'Advisors')
User.add_to_class('GROUP_AUTHORIZED_REPRESENTATIVE', 'AuthorizedRepresentatives') # TODO: would be nice to rename
User.add_to_class('GROUP_SUPERVISOR', 'Supervisors')
User.add_to_class('GROUP_CLIENT', 'Clients')


# TODO: update after modularization
User.add_to_class('PROFILES', {
    User.GROUP_ADVISOR: {'app_label': 'main', 'model_name': 'Advisor'},
    User.GROUP_AUTHORIZED_REPRESENTATIVE: {'app_label': 'main', 'model_name': 'AuthorisedRepresentative'},
    User.GROUP_SUPERVISOR: {'app_label': 'main', 'model_name': 'Supervisor'},
    User.GROUP_CLIENT: {'app_label': 'main', 'model_name': 'Client'},
    # add new profiles here
})


class SecurityQuestion(models.Model):
    """
    A Simple model to allow configuring a set of canned Security Questions
    """
    question = models.CharField(max_length=128, null=False, blank=False)

    def __str__(self):
        return _("%s") % self.question


class SecurityAnswer(models.Model):
    user = models.ForeignKey(User, db_index=True)
    # The question field is deliberately not a foreign key to the SecurityQuestion model because a user can create
    # their own questions if they desire.
    question = models.CharField(max_length=128, null=False, blank=False)
    # Answer is hashed using the same technique as passwords
    answer = models.CharField(max_length=128, null=False, blank=False)

    class Meta:
        unique_together = ('user', 'question')

    def __str__(self):
        return _("%s - %s") % (self.user, self.question)

    def hash_current_answer(self):
        self.set_answer(self.answer)

    def set_answer(self, raw_answer):
        if not bool(getattr(settings, "SECURITY_QUESTIONS_CASE_SENSITIVE", False)):
            raw_answer = raw_answer.upper()
        self.answer = hashers.make_password(raw_answer)

    def check_answer(self, raw_answer):
        if not bool(getattr(settings, "SECURITY_QUESTIONS_CASE_SENSITIVE", False)):
            raw_answer = raw_answer.upper()

        def setter(r_answer):
            self.set_answer(r_answer)
            self.save(update_fields=["answer"])
        return hashers.check_password(raw_answer, self.answer, setter)

    def set_unusable_answer(self):
        self.answer = hashers.make_password(None)

    def has_usable_answer(self):
        return hashers.is_password_usable(self.answer)

from . import connectors # just to init all the connectors, don't remove it


class EmailInvitation(models.Model):
    email = models.EmailField()
    inviter_type = models.ForeignKey(ContentType)
    inviter_id = models.PositiveIntegerField()
    inviter_object = GenericForeignKey('inviter_type', 'inviter_id')
    send_date = models.DateTimeField(auto_now=True)
    send_count = models.PositiveIntegerField(default=0)
    status = models.PositiveIntegerField(choices=constants.EMAIL_INVITATION_STATUSES,
                                         default=constants.INVITATION_PENDING)
    invitation_type = models.PositiveIntegerField(
        choices=constants.INVITATION_TYPE_CHOICES,
        default=constants.INVITATION_CLIENT)

    @property
    def get_status_name(self):
        for i in constants.EMAIL_INVITATION_STATUSES:
            if self.status == i[0]:
                return i[1]

    @property
    def get_status(self):
        try:
            user = User.objects.get(email=self.email)
        except User.DoesNotExist:
            user = None

        if user.prepopulated:
            return constants.INVITATION_PENDING

        if user is not None:
            if not user.is_active:
                self.status = constants.INVITATION_CLOSED
                self.save()

            for it in constants.INVITATION_TYPE_CHOICES:
                if self.invitation_type == it[0]:
                    model = constants.INVITATION_TYPE_DICT[str(it[0])]
                    if hasattr(user, model):
                        # match advisor or firm
                        profile = getattr(user, model)
                        if (profile.firm == self.inviter_object) or \
                                (getattr(profile, 'advisor', None) == self.inviter_object):
                            if profile.is_confirmed:
                                self.status = constants.INVITATION_ACTIVE
                                self.save()
                            else:
                                self.status = constants.INVITATION_SUBMITTED
                                self.save()
        return self.status

    def send(self):

        if self.get_status != constants.INVITATION_PENDING:
            return

        application_type = ""

        for itc in constants.INVITATION_TYPE_CHOICES:
            if itc[0] == self.invitation_type:
                application_type = itc[1]

        subject = "BetaSmartz {application_type} sign up form url".format(
            application_type=application_type)
        inviter_type = self.inviter_object.get_inviter_type()
        inviter_name = self.inviter_object.get_inviter_name()
        invite_url = self.inviter_object.get_invite_url(self.invitation_type, self.email)

        context = {
            'site': Site.objects.get_current(),
            'subject': subject,
            'invite_url': invite_url,
            'inviter_name': inviter_type,
            'inviter_class': inviter_name,
            'application_type': application_type
        }

        send_mail(subject,
                  '',
                  None,
                  [self.email],
                  html_message=render_to_string('email/invite.html', context))
        self.send_count += 1

        self.save()


class PlaidUser(models.Model):
    user = models.OneToOneField(User, related_name="plaid_user")
    access_token = models.CharField(max_length=255)


class StripeUser(models.Model):
    user = models.OneToOneField(User, related_name='stripe_user')
    account_id = models.CharField(max_length=255)

    def __str__(self):
        return 'StripeUser for %s' % self.user


# --------------------------------- Signals -----------------------------------


@receiver(user_logged_in)
def user_logged_in_notification(sender, user: User, **kwargs):
    user_types = ['client', 'advisor', 'supervisor',
                  'authorised_representative']
    for ut in user_types:
        try:
            Notify.SYSTEM_LOGIN.send(getattr(user, ut))
            break
        except ObjectDoesNotExist:
            pass


@receiver(user_logged_out)
def user_logged_out_notification(sender, user: User, **kwargs):
    if user is not None:
        # user was authenticated
        user_types = ['client', 'advisor', 'supervisor',
                      'authorised_representative']
        for ut in user_types:
            try:
                Notify.SYSTEM_LOGOUT.send(getattr(user, ut))
                break
            except ObjectDoesNotExist:
                pass
