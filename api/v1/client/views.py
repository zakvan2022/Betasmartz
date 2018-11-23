from django.contrib.auth import authenticate, login as auth_login
from django.contrib.sites.shortcuts import get_current_site
from django.http import Http404
from rest_framework import viewsets, views, mixins
from rest_framework import exceptions, parsers, status
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.viewsets import GenericViewSet
from rest_framework_extensions.mixins import NestedViewSetMixin
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import detail_route, list_route
from rest_framework.exceptions import ValidationError
from api.v1.client.serializers import EmailNotificationsSerializer, \
    PersonalInfoSerializer, RiskProfileResponsesSerializer
from api.v1.goals.serializers import GoalSerializer
from api.v1.permissions import IsClient, IsAccessAuthorised
from api.v1.retiresmartz.serializers import RetirementPlanEincSerializer, RetirementPlanEincWritableSerializer
from api.v1.user.serializers import UserSerializer
from api.v1.views import ApiViewMixin, ReadOnlyApiViewMixin
from client.models import Client, EmailInvite, ClientAccount, ExternalAsset
from goal.models import Goal
from main.constants import CLIENT_FULL_ACCESS
from main.risk_profiler import MINIMUM_RISK
from retiresmartz.models import RetirementPlan, RetirementPlanEinc, RetirementAdvice
from support.models import SupportRequest
from user.models import SecurityAnswer
from user.models import User
from django.views.generic.detail import SingleObjectMixin
from . import serializers
import logging
import json
import time
from api.v1.utils import activity
from django.template.loader import render_to_string
from main import quovo, plaid
from client import healthdevice
from address.models import USState, USFips, USZipcode
from consumer_expenditure.models import AreaQuotient, PeerGroupData
from consumer_expenditure import utils as ce_utils
from functools import reduce
from brokers.interactive_brokers.onboarding import onboarding
logger = logging.getLogger('api.v1.client.views')


class ExternalAssetViewSet(ApiViewMixin, NestedViewSetMixin, viewsets.ModelViewSet):
    model = ExternalAsset
    # We define the queryset because our get_queryset calls super so the Nested queryset works.
    queryset = ExternalAsset.objects.all()
    serializer_class = serializers.ExternalAssetSerializer
    pagination_class = None

    # Set the response serializer because we want to use the 'get' serializer for responses from the 'create' methods.
    # See api/v1/views.py
    serializer_response_class = serializers.ExternalAssetSerializer

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'POST']:
            return serializers.ExternalAssetWritableSerializer
        else:
            # Default for get and other requests is the read only serializer
            return serializers.ExternalAssetSerializer

    def get_queryset(self):
        qs = super(ExternalAssetViewSet, self).get_queryset()

        # Only return assets which the user has access to.
        user = SupportRequest.target_user(self.request)
        return qs.filter_by_user(user)


class RetirementIncomeViewSet(ApiViewMixin, NestedViewSetMixin, viewsets.ModelViewSet):
    model = RetirementPlanEinc
    # We define the queryset because our get_queryset calls super so the Nested queryset works.
    queryset = RetirementPlanEinc.objects.all()
    serializer_class = RetirementPlanEincSerializer
    pagination_class = None

    # Set the response serializer because we want to use the 'get' serializer for responses from the 'create' methods.
    # See api/v1/views.py
    serializer_response_class = RetirementPlanEincSerializer

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'POST']:
            return RetirementPlanEincWritableSerializer
        else:
            # Default for get and other requests is the read only serializer
            return RetirementPlanEincSerializer

    def get_queryset(self):
        qs = super(RetirementIncomeViewSet, self).get_queryset()

        # Only return assets which the user has access to.
        user = SupportRequest.target_user(self.request)
        allow_plans = RetirementPlan.objects.filter_by_user(user)
        return qs.filter(plan__in=allow_plans)


class ClientViewSet(ApiViewMixin,
                    NestedViewSetMixin,
                    mixins.CreateModelMixin,
                    mixins.RetrieveModelMixin,
                    mixins.UpdateModelMixin,
                    mixins.ListModelMixin,
                    GenericViewSet):
    """
    Everything except delete
    """
    model = Client
    # We define the queryset because our get_queryset calls super so the Nested queryset works.
    queryset = Client.objects.all()
    serializer_class = serializers.ClientSerializer
    # Set the response serializer because we want to use the 'get' serializer for responses from the 'create' methods.
    # See api/v1/views.py
    serializer_response_class = serializers.ClientSerializer
    pagination_class = None

    def get_serializer_class(self):
        if self.request.method in ['PUT']:
            return serializers.ClientUpdateSerializer
        elif self.request.method in ['POST']:
            return serializers.ClientCreateSerializer
        else:
            # Default for get and other requests is the read only serializer
            return serializers.ClientSerializer

    def get_queryset(self):
        qs = super(ClientViewSet, self).get_queryset()

        # Only return Clients the user has access to.
        user = SupportRequest.target_user(self.request)
        return qs.filter_by_user(user)

    def get_object(self):
        try:
            obj = super(ClientViewSet, self).get_object()
        except Http404:
            raise exceptions.PermissionDenied("You do not have permission to perform this action.")
        return obj

    def create(self, request, *args, **kwargs):

        invitation = request.user.invitation
        if not hasattr(request.user, 'invitation') or EmailInvite.STATUS_ACCEPTED != getattr(invitation,
                                                                                             'status',
                                                                                             None):
            return Response({'error': 'requires account with accepted invitation'},
                            status=status.HTTP_405_METHOD_NOT_ALLOWED)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # creat new client
        readonly_access = (invitation.access_level != CLIENT_FULL_ACCESS)
        client = serializer.save(advisor=request.user.invitation.advisor, user=request.user,
                                 readonly_access=readonly_access,
                                 risk_score=invitation.risk_score)

        # calculate risk score from risk profile responses if advisor did not specify risk score
        if not invitation.risk_score:
            bas_scores = client.get_risk_profile_bas_scores()
            if not bas_scores:
                recommend_risk = MINIMUM_RISK
            else:
                recommend_risk = min(1., max(0., min(bas_scores)))

            client.risk_score = recommend_risk
            client.save()

        # if client accepted agreement (stripe TOS link should be at bottom) then set agreement time and ip
        if client.betasmartz_agreement is True:
            client.agreement_time = int(time.time())
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                client.agreement_ip = x_forwarded_for.split(',')[0]
            else:
                client.agreement_ip = request.META.get('REMOTE_ADDR')
            client.save()

        if isinstance(client.regional_data, dict):
            rd = client.regional_data
        else:
            rd = json.loads(client.regional_data)
        if not rd.get('tax_transcript_data'):
            # add tax_transcript and tax_transcript_data from
            # the invitation serializer to client.regional_data
            invitation_serializer = serializers.PrivateInvitationSerializer(request.user.invitation)
            if invitation_serializer.data.get('tax_transcript', None) is not None:
                rd['tax_transcript'] = invitation_serializer.data.get('tax_transcript')
                rd['tax_transcript_data'] = invitation_serializer.data.get('tax_transcript_data')
                client.regional_data = json.dumps(rd)
                client.save()

        if not rd.get('social_security_statement_data'):
            # add social_security_statement and social_security_statement_data from
            # the invitation serializer to client.regional_data
            invitation_serializer = serializers.PrivateInvitationSerializer(request.user.invitation)
            if invitation_serializer.data.get('social_security_statement', None) is not None:
                rd['social_security_statement'] = invitation_serializer.data.get('social_security_statement')
                rd['social_security_statement_data'] = invitation_serializer.data.get('social_security_statement_data')
                client.regional_data = json.dumps(rd)
                client.save()

        if not rd.get('partner_social_security_statement_data'):
            # add social_security_statement and social_security_statement_data from
            # the invitation serializer to client.regional_data
            invitation_serializer = serializers.PrivateInvitationSerializer(request.user.invitation)
            if invitation_serializer.data.get('partner_social_security_statement', None) is not None:
                rd['partner_social_security_statement'] = invitation_serializer.data.get('partner_social_security_statement')
                rd['partner_social_security_statement_data'] = invitation_serializer.data.get('partner_social_security_statement_data')
                client.regional_data = json.dumps(rd)
                client.save()

        # set client invitation status to complete
        client.user.invitation.status = EmailInvite.STATUS_COMPLETE
        client.user.invitation.save()

        # Email the user "Welcome Aboard"
        subject = 'Welcome to {}!'.format(client.firm.name)
        context = {
            'site': get_current_site(request),
            'advisor': client.advisor,
            'login_url': client.user.login_url,
            'category': 'Customer onboarding'
        }
        self.request.user.email_user(subject,
                                     html_message=render_to_string(
                                        'email/client/congrats_new_client_setup.html', context))

        headers = self.get_success_headers(serializer.data)
        serializer = self.serializer_response_class(client)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        kwargs['partial'] = True
        partial = kwargs.pop('partial', False)
        serializer = self.get_serializer(instance, data=request.data, partial=partial, context={'request': request})
        serializer.is_valid(raise_exception=True)
        updated = serializer.update(instance, serializer.validated_data)
        return Response(self.serializer_response_class(updated).data)

    @detail_route(methods=['get'], permission_classes=[IsAccessAuthorised,])
    def goals(self, request, pk=None, **kwargs):
        """
        Return list of goals from all accounts of the given client
        """
        instance = self.get_object()
        accounts = ClientAccount.objects.filter(primary_owner=instance)
        goals = Goal.objects.filter(account__in=accounts)
        serializer = GoalSerializer(goals, many=True)
        return Response(serializer.data)

    @detail_route(methods=['get'])
    def activity(self, request, pk=None, **kwargs):
        """
        Return list of activities from all accounts of the given client
        """
        client = self.get_object()
        return activity.get(request, client)

    @detail_route(methods=['put'], permission_classes=[IsAccessAuthorised,], url_path='risk-profile-responses')
    def risk_profile_responses(self, request, pk=None, **kwargs):
        instance = self.get_object()
        serializer = RiskProfileResponsesSerializer(instance, data={'risk_profile_responses':request.data})
        serializer.is_valid(raise_exception=True)
        client = serializer.save()
        return Response(serializer.data['risk_profile_responses'])

    @detail_route(methods=['get'], permission_classes=[IsAccessAuthorised,], url_path='peer-group-expenses/')
    def peer_group_expenses(self, request, pk=None, **kwargs):
        client = self.get_object()
        yearly_income = float(request.GET.get('income', client.income))
        age_group = ce_utils.get_age_group(client.age)
        state = USState.objects.get(code=client.residential_address.region.code)
        region_no = state.region
        region_col = ce_utils.get_region_column_name(region_no)
        # zipcodes = USZipcode.objects.filter(zip_code=client.residential_address.post_code)
        # rucc = zipcodes[0].fips.rucc
        # loc_col = ce_utils.get_location_column_name(rucc)
        pc_col = ce_utils.get_pc_column_name(yearly_income)
        tax_cat = expense_cat=RetirementPlan.ExpenseCategory.TAXES.value
        tax_item = PeerGroupData.objects.get(age_group=age_group, expense_cat=tax_cat)
        ep_pgd = getattr(tax_item, pc_col) # Expenditure from peer group data
        region_quot = getattr(tax_item, region_col) # Location quotient region
        tax_rate = region_quot * ep_pgd

        peer_group_data = PeerGroupData.objects.filter(
            age_group=age_group
        ).exclude(
            expense_cat=RetirementPlan.ExpenseCategory.TAXES.value
        )

        results = []
        for item in peer_group_data:
            ep_pgd = getattr(item, pc_col) # Expenditure from peer group data
            region_quot = getattr(item, region_col) # Location quotient region
            results += [{
                'cat': item.expense_cat.id,
                'adj_ep_based_100': region_quot * ep_pgd # Adjusted % Expenditure based to 100%
            }]

        ep_sum = reduce((lambda acc, item: acc + item['adj_ep_based_100']), results, 0.0)
        descriptions = ce_utils.get_category_descriptions()
        def build_response_item(item):
            return {
                'id': item['cat'],
                'cat': item['cat'],
                'who': 'self',
                'desc': descriptions[item['cat']],
                'rate': item['adj_ep_based_100'] / ep_sum,
            }

        results = list(map(build_response_item, results))
        results += [{
            'id': tax_cat,
            'cat': tax_cat,
            'who': 'self',
            'desc': descriptions[tax_cat],
            'rate': tax_rate,
        }]

        return Response(results)

    @detail_route(methods=['get'], permission_classes=[IsClient,], url_path='health-device-data/')
    def get_health_device_data(self, request, *args, **kwargs):
        user = SupportRequest.target_user(request)
        data = healthdevice.get_data(user.client)
        if data is None:
            raise exceptions.ParseError('Failed to get data from your health device')
        data['id'] = user.client.id
        return Response(data)

    @detail_route(methods=['delete'], permission_classes=[IsClient,], url_path='remove-health-device/')
    def remove_health_device(self, request, *args, **kwargs):
        user = SupportRequest.target_user(request)
        try:
            user.client.health_device.delete()
        except:
            raise exceptions.NotFound('You do not have a health device connected')
        return Response('ok')


class InvitesView(ApiViewMixin, views.APIView):
    permission_classes = []
    serializer_class = serializers.PrivateInvitationSerializer
    parser_classes = (
        parsers.FormParser, parsers.MultiPartParser, parsers.JSONParser,
    )

    def get(self, request, invite_key):
        find_invite = EmailInvite.objects.filter(invite_key=invite_key)
        if not find_invite.exists:
            return Response({'error': 'invitation not found'}, status=status.HTTP_404_NOT_FOUND)

        invite = find_invite.get()

        if request.user.is_authenticated():
            # include onboarding data
            data = self.serializer_class(instance=invite).data
        else:
            data = serializers.InvitationSerializer(instance=invite).data
        return Response(data)

    def put(self, request, invite_key):
        if not request.user.is_authenticated():
            return Response({'error': 'not logged in'}, status=status.HTTP_401_UNAUTHORIZED)

        find_invite = EmailInvite.objects.filter(invite_key=invite_key)
        if not find_invite.exists:
            return Response({'error': 'invitation not found'}, status=status.HTTP_404_NOT_FOUND)

        invite = find_invite.get()

        if invite.status == EmailInvite.STATUS_EXPIRED:
            invite.advisor.user.email_user('A client tried to use an expired invitation'
                                           "Your potential client {} {} ({}) just tried to register using an invite "
                                           "you sent them, but it has expired!".format(invite.first_name,
                                                                                       invite.last_name,
                                                                                       invite.email))

        if invite.status != EmailInvite.STATUS_ACCEPTED:
            return Response(self.serializer_class(instance=invite).data,
                            status=status.HTTP_304_NOT_MODIFIED)

        serializer = self.serializer_class(invite, data=request.data, partial=True)
        if serializer.is_valid(raise_exception=True):
            serializer.save()

        return Response(serializer.data)


class ClientUserRegisterView(ApiViewMixin, views.APIView):
    """
    Register Client's User from an invite token
    """
    permission_classes = []
    serializer_class = serializers.ClientUserRegistrationSerializer

    def post(self, request):
        user = SupportRequest.target_user(request)
        if user.is_authenticated():
            raise exceptions.PermissionDenied("Another user is already logged in.")

        serializer = serializers.ClientUserRegistrationSerializer(data=request.data)
        if not serializer.is_valid(raise_exception=True):
            logger.error('Error accepting invitation: %s' % serializer.errors['non_field_errors'][0])
            return Response({'error': 'invitation not found for this email'}, status=status.HTTP_404_NOT_FOUND)
        invite = serializer.invite

        user_params = {
            'email': invite.email,
            'username': invite.email,
            'first_name': invite.first_name,
            'middle_name': invite.middle_name,
            'last_name': invite.last_name,
            'password': serializer.validated_data['password'],
        }
        user = User.objects.create_user(**user_params)

        sa1 = SecurityAnswer(user=user, question=serializer.validated_data['question_one'])
        sa1.set_answer(serializer.validated_data['question_one_answer'])
        sa1.save()

        sa2 = SecurityAnswer(user=user, question=serializer.validated_data['question_two'])
        sa2.set_answer(serializer.validated_data['question_two_answer'])
        sa2.save()

        invite.status = EmailInvite.STATUS_ACCEPTED
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
        msg = "Your client %s %s (%s) has accepted your invitation to Betasmartz!" % (user.first_name,
                                                                                      user.last_name,
                                                                                      user.email)
        invite.advisor.user.email_user('Client has accepted your invitation', msg)
        return Response(user_serializer.data)


class EmailNotificationsView(ApiViewMixin, RetrieveUpdateAPIView):
    permission_classes = IsClient,
    serializer_class = EmailNotificationsSerializer

    def get_object(self):
        return Client.objects.get(user=self.request.user).notification_prefs


class ProfileView(ApiViewMixin, RetrieveUpdateAPIView):
    permission_classes = IsClient,
    serializer_class = PersonalInfoSerializer

    def get_object(self):
        return Client.objects.get(user=self.request.user)


class ClientResendInviteView(SingleObjectMixin, views.APIView):
    permission_classes = [IsAuthenticated, ]
    queryset = EmailInvite.objects.all()

    def post(self, request, invite_key):
        find_invite = EmailInvite.objects.filter(invite_key=invite_key)
        if not find_invite.exists:
            raise exceptions.NotFound("Invitation not found.")

        invite = find_invite.get()

        if invite.user != self.request.user:
            raise exceptions.PermissionDenied("You are not authorized to send invitation.")

        invite.send()
        return Response('ok', status=status.HTTP_200_OK)


class TargetUserMixin(object):
    def get_target_user(self, request):
        if 'client' in self.get_parents_query_dict():
            client_id = int(self.get_parents_query_dict()['client'])
            user = SupportRequest.target_user(request)
            clients = Client.objects.filter_by_user(user).filter(pk=client_id)
            if clients.count() == 0:
                raise exceptions.PermissionDenied("You do not have permission to access plaid accounts")
            return clients[0].user
        else:
            return request.user

class PlaidViewSet(ApiViewMixin, GenericViewSet, NestedViewSetMixin, TargetUserMixin):
    @list_route(methods=['post'], permission_classes=[IsAuthenticated,], url_path='create-access-token')
    def create_access_token(self, request, *args, **kwargs):
        target_user = self.get_target_user(request)
        public_token = request.data.get('public_token', None)
        if public_token is None:
            return Response('missing public_token', status=status.HTTP_400_BAD_REQUEST)
        success = plaid.create_access_token(target_user, public_token)
        if not success:
            raise ValidationError('Failed to create plaid access token')
        data = {"success": success}
        return Response(data)

    @list_route(methods=['get'], permission_classes=[IsAuthenticated,], url_path='get-accounts')
    def get_accounts(self, request, *args, **kwargs):
        target_user = self.get_target_user(request)
        data = plaid.get_accounts(target_user)
        return Response(data)


class QuovoViewSet(ApiViewMixin, GenericViewSet, NestedViewSetMixin, TargetUserMixin):
    @list_route(methods=['get'], permission_classes=[IsAuthenticated,], url_path='get-iframe-token')
    def get_iframe_token(self, request, *args, **kwargs):
        target_user = self.get_target_user(request)
        token = quovo.get_iframe_token(request, target_user)
        data = {"token": token}
        return Response(data)

    @list_route(methods=['get'], permission_classes=[IsAuthenticated,], url_path='get-accounts')
    def get_accounts(self, request, *args, **kwargs):
        target_user = self.get_target_user(request)
        data = quovo.get_accounts(request, target_user)
        return Response(data)


class IbOnboardingView(ReadOnlyApiViewMixin, views.APIView):
    permission_classes = [IsAuthenticated, ]
    renderer_classes = (JSONRenderer,)

    def post(self, request, *args, **kwargs):
        success = onboarding.onboard('INDIVIDUAL', request.user, public_token)
        data = {"success": success}
        return Response(data)
