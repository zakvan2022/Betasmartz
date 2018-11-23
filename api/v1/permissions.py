from rest_framework import permissions

from client.models import Client
from advisor.models import Advisor
from support.models import SupportRequest

__all__ = ['IsClient', 'IsAdvisor', 'IsSupportStaff', 'IsAdvisorOrClient', 'IsAccessAuthorised']


def is_support_staff(request):
    try:
        return SupportRequest.get_current(request) and \
               request.user.is_support_staff
    except AttributeError:  # anonymous users don't have `is_support_staff`
        pass


class IsSupportStaff(permissions.BasePermission):
    def has_permission(self, request, view):
        return is_support_staff(request)


class IsAdvisor(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated() and (
            is_support_staff(request) or request.user.is_advisor
        )


class IsClient(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated() and (
            is_support_staff(request) or request.user.is_client
        )


class IsSupervisor(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated() and (
            is_support_staff(request) or request.user.is_supervisor
        )


class IsAuthorisedRepresentative(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated() and (
            is_support_staff(request) or request.user.is_authorised_representative
        )


class IsAdvisorOrClient(IsClient, IsAdvisor):
    def has_permission(self, request, view):
        return request.user.is_authenticated() and (
            is_support_staff(request) or
            request.user.is_advisor or request.user.is_client
        )


class IsAccessAuthorised(IsClient, IsAdvisor, IsAuthorisedRepresentative, IsSupervisor):
    def has_permission(self, request, view):
        return request.user.is_authenticated() and (
            is_support_staff(request) or
            request.user.is_advisor or request.user.is_client or
            request.user.is_authorised_representative or request.user.is_supervisor
        )


# RESERVED
class IsMyAdvisorCompany(IsAdvisor):
    """
    Note: user is supposed to be Advisor only
    (could be extrended later)
    """

    def has_permission(self, request, view):
        user = request.user

        if not user.is_advisor:
            return True

        advisor = user.advisor

        if not advisor.company:
            # advisor should be associated with an advisor company
            return False

        return True

    def has_object_permission(self, request, view, obj):
        user = request.user

        if not user.is_advisor:
            return True

        advisor = user.advisor

        if isinstance(obj, Advisor):
            return obj.company == advisor.company

        if isinstance(obj, Client):
            # "get_clients" supposed to be role-awared
            try:
                advisor.get_clients().get(pk=obj.pk)
                return True
            except Client.DoesNotExist:
                return False

        else:
            # reserved
            pass


# RESERVED
class IsMyAdvisorCompanyCustom(IsMyAdvisorCompany):
    """
    Helper to be used for viewsets passing custom "object"

    Note: user is supposed to be Advisor only
    (could be extrended later)
    """

    def __init__(self, obj=None):
        super(IsMyAdvisorCompanyCustom, self).__init__()
        if obj:
            self.obj = obj

    def has_permission(self, request, view):
        if hasattr(self, 'obj'):
            return (super(IsMyAdvisorCompanyCustom, self)
                    .has_object_permission(request, view, self.obj))

        return True

    def has_object_permission(self, request, view, obj):
        if hasattr(self, 'obj'):
            # already checked above (see "has_permission" function)
            return True

        return (super(IsMyAdvisorCompanyCustom, self)
                .has_object_permission(request, view, obj))


# RESERVED
def IsMyAdvisorCompanyCustomInit(obj):
    """
    Generate permission class with custom attributes.
    Supposed to be used for view sets passing custom "object"

    PS. Let's keep it capitalized to mimic a class.
    """
    IsMyAdvisorCompanyCustomClass = type(
        'IsMyAdvisorCompanyNested',
        (IsMyAdvisorCompanyCustom,),
        {'obj': obj},
    )

    return IsMyAdvisorCompanyCustomClass
