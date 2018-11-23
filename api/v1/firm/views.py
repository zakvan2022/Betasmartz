# -*- coding: utf-8 -*-
import time
import logging
from . import serializers
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from rest_framework.generics import RetrieveAPIView
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from api.v1.views import ApiViewMixin
from firm.models import Firm, AuthorisedRepresentative
from support.models import SupportRequest
from .serializers import FirmSerializer
from ..address.serializers import UNSET_ADDRESS
from ..advisor.serializers import AdvisorUserCreateSerializer, AdvisorCreateSerializer
from rest_framework.response import Response
from rest_framework import viewsets, views, mixins
from rest_framework import exceptions, parsers, status
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.viewsets import GenericViewSet
from rest_framework_extensions.mixins import NestedViewSetMixin
from firm.models import FirmEmailInvite
from user.models import SecurityAnswer
from django.template.loader import render_to_string
from api.v1.user.serializers import UserSerializer
from user.models import User
from django.views.generic.detail import SingleObjectMixin


logger = logging.getLogger('api.v1.firm.views')


class FirmSingleView(ApiViewMixin, RetrieveAPIView):
    serializer_class = FirmSerializer

    def get(self, request, pk):
        user = SupportRequest.target_user(request)
        serializer = None
        if user.is_advisor:
            if user.advisor.firm.pk == int(pk):
                serializer = self.serializer_class(user.advisor.firm)
        elif user.is_authorised_representative:
            if user.authorised_representative.firm.pk == int(pk):
                serializer = self.serializer_class(user.authorised_representative.firm)
        elif user.is_supervisor:
            if user.supervisor.firm.pk == int(pk):
                serializer = self.serializer_class(user.supervisor.firm)
        elif user.is_client:
            # make sure user is a client of the requested firm
            if user.client.advisor.firm.pk == int(pk):
                serializer = self.serializer_class(user.client.advisor.firm)

        if serializer:
            return Response(serializer.data)
        return self.permission_denied(request)


class FirmRequestOnboardingView(ApiViewMixin, views.APIView):
    permission_classes = []
    serializer_class = serializers.FirmInvitationCreateSerializer
    serializer_response_class = serializers.FirmInvitationSerializer
    parser_classes = (
        parsers.FormParser, parsers.MultiPartParser, parsers.JSONParser,
    )

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        invite = serializer.save()
        invite.send()
        return Response(self.serializer_response_class(invite).data, status=status.HTTP_201_CREATED)


class RepresentativeViewSet(ApiViewMixin,
                            NestedViewSetMixin,
                            mixins.CreateModelMixin,
                            mixins.RetrieveModelMixin,
                            mixins.UpdateModelMixin,
                            mixins.ListModelMixin,
                            GenericViewSet):
    """
    Everything except delete
    """
    model = AuthorisedRepresentative
    # We define the queryset because our get_queryset calls super so the Nested queryset works.
    queryset = AuthorisedRepresentative.objects.all()
    serializer_class = serializers.AuthorisedRepresentativeSerializer
    # Set the response serializer because we want to use the 'get' serializer for responses from the 'create' methods.
    # See api/v1/views.py
    serializer_response_class = serializers.AuthorisedRepresentativeSerializer
    pagination_class = None

    def get_serializer_class(self):
        if self.request.method in ['PUT']:
            return serializers.AuthorisedRepresentativeUpdateSerializer
        elif self.request.method in ['POST']:
            return serializers.AuthorisedRepresentativeCreateSerializer
        else:
            # Default for get and other requests is the read only serializer
            return serializers.AuthorisedRepresentativeSerializer

    def get_queryset(self):
        qs = super(RepresentativeViewSet, self).get_queryset()

        # Only return Clients the user has access to.
        user = SupportRequest.target_user(self.request)
        return qs.filter_by_user(user)

    def create_advisors(self, request, advisors, firm):
        if not advisors or len(advisors) == 0:
            return
        for item in advisors:
            password = User.objects.make_random_password()
            user_fields = item.copy()
            user_fields.update({'password': password})
            user_ser = AdvisorUserCreateSerializer(data=user_fields)
            user_ser.is_valid(raise_exception=True)
            user = user_ser.save()

            advisor_fields = {
                'residential_address': UNSET_ADDRESS,
                'work_phone_num': item.get('work_phone_num', None),
                'firm': firm.pk
            }
            advisor_ser = AdvisorCreateSerializer(data=advisor_fields)
            advisor_ser.is_valid(raise_exception=True)
            advisor = advisor_ser.save(betasmartz_agreement=True, user=user,
                             default_portfolio_set=firm.default_portfolio_set)

            # Email the user "Welcome Aboard"
            site = get_current_site(request)
            subject = 'Welcome to {}!'.format(site.name)
            context = {
                'site': site,
                'advisor': advisor,
                'login_url': advisor.user.login_url,
                'password': password
            }
            self.request.user.email_user(subject,
                                         html_message=render_to_string(
                                            'email/advisor/congrats_new_advisor_setup.html', context))

    def create(self, request, *args, **kwargs):
        try:
            invitation = request.user.firm_invitation
        except Exception:
            return Response({'error': 'firm invitation not found for user'},
                            status=status.HTTP_400_BAD_REQUEST)

        if not hasattr(request.user, 'firm_invitation') or FirmEmailInvite.STATUS_ACCEPTED != getattr(invitation,
                                                                                                      'status',
                                                                                                      None):
            return Response({'error': 'requires account with accepted invitation'},
                            status=status.HTTP_405_METHOD_NOT_ALLOWED)

        with transaction.atomic():  # So both the log and change get committed.
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            # creat new authorised representative
            rep = serializer.save(user=request.user, is_accepted=True, is_confirmed=True)
            # if agreement is set, save time and ip
            if rep.betasmartz_agreement is True:
                rep.agreement_time = int(time.time())
                x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
                if x_forwarded_for:
                    rep.agreement_ip = x_forwarded_for.split(',')[0]
                else:
                    rep.agreement_ip = request.META.get('REMOTE_ADDR')
                rep.save()

            if 'advisors' in request.data:
                self.create_advisors(request, request.data.get('advisors'), rep.firm)

            # set authorised representative invitation status to complete
            rep.user.firm_invitation.status = FirmEmailInvite.STATUS_COMPLETE
            rep.user.firm_invitation.save()

        # Email the user "Welcome Aboard"
        subject = 'Welcome to {}!'.format(rep.firm.name)
        context = {
            'firm': rep.firm,
            'login_url': rep.user.login_url,
            'category': 'Firm onboarding'
        }
        self.request.user.email_user(subject,
                                     html_message=render_to_string('email/firm/congrats_new_rep_setup.html', context))

        headers = self.get_success_headers(serializer.data)
        serializer = self.serializer_response_class(rep)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        kwargs['partial'] = True
        partial = kwargs.pop('partial', False)
        serializer = self.get_serializer(instance, data=request.data, partial=partial, context={'request': request})
        serializer.is_valid(raise_exception=True)
        updated = serializer.update(instance, serializer.validated_data)
        return Response(self.serializer_response_class(updated).data)


class FirmInvitesView(ApiViewMixin, views.APIView):
    permission_classes = []
    serializer_class = serializers.PrivateFirmInvitationSerializer
    parser_classes = (
        parsers.FormParser, parsers.MultiPartParser, parsers.JSONParser,
    )

    def get(self, request, invite_key):
        find_invite = FirmEmailInvite.objects.filter(invite_key=invite_key)
        if not find_invite.exists:
            return Response({'error': 'invitation not found'}, status=status.HTTP_404_NOT_FOUND)

        invite = find_invite.get()

        if request.user.is_authenticated():
            # include onboarding data
            data = self.serializer_class(instance=invite).data
        else:
            data = serializers.FirmInvitationSerializer(instance=invite).data
        return Response(data)

    def put(self, request, invite_key):
        if not request.user.is_authenticated():
            return Response({'error': 'not logged in'}, status=status.HTTP_401_UNAUTHORIZED)

        find_invite = FirmEmailInvite.objects.filter(invite_key=invite_key)
        if not find_invite.exists:
            return Response({'error': 'invitation not found'}, status=status.HTTP_404_NOT_FOUND)

        invite = find_invite.get()

        if invite.status == FirmEmailInvite.STATUS_EXPIRED:
            invite.user.email_user('You tried to use an expired invitation'
                                   "Your potential client {} {} ({}) just tried to register using an invite "
                                   "you sent them, but it has expired!".format(invite.first_name,
                                                                               invite.last_name,
                                                                               invite.email))

        if invite.status != FirmEmailInvite.STATUS_ACCEPTED:
            return Response(self.serializer_class(instance=invite).data,
                            status=status.HTTP_304_NOT_MODIFIED)

        serializer = self.serializer_class(invite, data=request.data, partial=True)
        if serializer.is_valid(raise_exception=True):
            serializer.save()

        return Response(serializer.data)


class FirmUserRegisterView(ApiViewMixin, views.APIView):
    """
    Register Firm's Initial Authorised Representative User from an invite token
    """
    permission_classes = []
    serializer_class = serializers.FirmUserRegistrationSerializer

    def post(self, request):
        user = SupportRequest.target_user(request)
        if user.is_authenticated():
            raise exceptions.PermissionDenied("Another user is already logged in.")

        serializer = serializers.FirmUserRegistrationSerializer(data=request.data)
        if not serializer.is_valid(raise_exception=True):
            logger.error('Error accepting invitation: %s' % serializer.errors['non_field_errors'][0])
            return Response({'error': 'invitation not found for this email'}, status=status.HTTP_404_NOT_FOUND)
        invite = serializer.invite

        user_params = {
            'email': serializer.validated_data['email'],
            'username': serializer.validated_data['email'],
            'first_name': serializer.validated_data['first_name'],
            'middle_name': serializer.validated_data['middle_name'],
            'last_name': serializer.validated_data['last_name'],
            'password': serializer.validated_data['password'],
        }
        user = User.objects.create_user(**user_params)

        if 'question_one' in serializer.validated_data:
            sa1 = SecurityAnswer(user=user, question=serializer.validated_data['question_one'])
            sa1.set_answer(serializer.validated_data['question_one_answer'])
            sa1.save()

        if 'question_two' in serializer.validated_data:
            sa2 = SecurityAnswer(user=user, question=serializer.validated_data['question_two'])
            sa2.set_answer(serializer.validated_data['question_two_answer'])
            sa2.save()

        invite.status = FirmEmailInvite.STATUS_ACCEPTED
        invite.user = user

        invite.save()

        login_params = {
            'username': user.email,
            'password': serializer.validated_data['password']
        }

        user = authenticate(**login_params)

        # check if user is authenticated
        if not user or not user.is_authenticated():
            raise exceptions.NotAuthenticated()

        # Log the user in with a session as well.
        auth_login(request, user)

        user_serializer = UserSerializer(instance=user)
        return Response(user_serializer.data)


class FirmResendInviteView(SingleObjectMixin, views.APIView):
    permission_classes = [IsAuthenticated, ]
    queryset = FirmEmailInvite.objects.all()

    def post(self, request, invite_key):
        find_invite = FirmEmailInvite.objects.filter(invite_key=invite_key)
        if not find_invite.exists:
            raise exceptions.NotFound("Invitation not found.")

        invite = find_invite.get()

        if invite.user != self.request.user:
            raise exceptions.PermissionDenied("You are not authorized to send invitation.")

        invite.send()
        return Response('ok', status=status.HTTP_200_OK)
