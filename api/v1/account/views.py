import logging

from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.db import transaction
from django.db.models.query_utils import Q
from django.template import RequestContext
from django.template.loader import render_to_string
from django.utils.functional import curry
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import detail_route, list_route
from rest_framework.exceptions import NotFound, PermissionDenied, \
    ValidationError
from rest_framework.response import Response
from rest_framework_extensions.mixins import NestedViewSetMixin

from api.v1.permissions import IsAdvisorOrClient, IsAccessAuthorised
from api.v1.utils import activity
from api.v1.views import ApiViewMixin
from client.models import AccountBeneficiary, ClientAccount, \
    CloseAccountRequest, JointAccountConfirmationModel
from main import constants
from user.models import User
from multi_sites.models import AccountType
from support.models import SupportRequest
from . import serializers

logger = logging.getLogger(__name__)



class AccountViewSet(ApiViewMixin,
                     NestedViewSetMixin,
                     mixins.UpdateModelMixin,
                     mixins.CreateModelMixin,
                     viewsets.ReadOnlyModelViewSet):
    model = ClientAccount
    # We define the queryset because our get_queryset calls super so the Nested queryset works.
    queryset = ClientAccount.objects.all()
    pagination_class = None

    permission_classes = (IsAccessAuthorised,)

    # Set the response serializer because we want to use the 'get' serializer for responses from the 'create' methods.
    # See api/v1/views.py
    serializer_response_class = serializers.ClientAccountSerializer

    # Override this method so we can also look for accounts from signatories
    def filter_queryset_by_parents_lookups(self, queryset):
        parents_query_dict = self.get_parents_query_dict()
        if parents_query_dict:
            q = None
            try:
                for key, value in parents_query_dict.items():
                    if key == 'primary_owner':
                        tq = (Q(primary_owner=value) | Q(signatories__id=value))
                    else:
                        tq = Q({key: value})
                    if q:
                        q &= tq
                    else:
                        q = tq

                return queryset.filter(q)
            except ValueError:
                raise NotFound()
        else:
            return queryset

    def get_serializer_class(self):
        if self.request.method == 'PUT':
            return serializers.ClientAccountUpdateSerializer
        elif self.request.method == 'POST':
            return serializers.ClientAccountCreateSerializer
        else:
            # Default for get and other requests is the read only serializer
            return serializers.ClientAccountSerializer

    def get_queryset(self):
        """
        Because this viewset can have a primary owner and signatories,
        we don't use the queryset parsing features from NestedViewSetMixin as
        it only allows looking at one field for the parent.
        :return:
        """
        qs = super(AccountViewSet, self).get_queryset()

        # show "permissioned" records only
        user = SupportRequest.target_user(self.request)
        if user.is_advisor:
            qs = qs.filter_by_advisor(user.advisor)
        elif user.is_client:
            qs = qs.filter_by_client(user.client)
        elif user.is_supervisor:
            qs = qs.filter_by_supervisor(user.supervisor)
        elif user.is_authorised_representative:
            qs = qs.filter_by_authorised_representative(user.authorised_representative)
        else:
            raise PermissionDenied('You do not have sufficient permission to access accounts.')

        return qs

    @detail_route(methods=['get'])
    def activity(self, request, pk=None, **kwargs):
        account = self.get_object()
        return activity.get(request, account)

    def create(self, request):
        """
        only allow one personal account per client
        """

        klass = self.get_serializer_class()
        serializer = klass(data=request.data)

        if serializer.is_valid():
            owner = serializer.validated_data['primary_owner']
            other_personals = owner.primary_accounts.filter(account_type=constants.ACCOUNT_TYPE_PERSONAL)
            if serializer.validated_data['account_type'] == constants.ACCOUNT_TYPE_PERSONAL \
                    and other_personals.count() >= 1:
                return Response({'error': 'Limit 1 personal account'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
            firm = serializer.validated_data['primary_owner'].advisor.firm
            if not firm.account_types.filter(id=serializer.validated_data['account_type']).exists():
                emsg = 'Account Type: {} is not active for {}'
                a_t = AccountType.objects.filter(id=serializer.validated_data['account_type']).first()
                return Response({'error': emsg.format(a_t, firm)}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
            if serializer.validated_data['account_type'] in constants.US_RETIREMENT_ACCOUNT_TYPES:
                emsg = 'US Retirement account types are not user creatable.'
                return Response({'error': emsg}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
        return super(AccountViewSet, self).create(request)

    def perform_create(self, serializer):
        object = super(AccountViewSet, self).perform_create(serializer)  # type: ClientAccount
        autoconfirm = object.account_type in settings.AUTOCONFIRMED_ACCOUNTS
        if autoconfirm and not object.confirmed:
            object.confirmed = True
            object.save()
        return object

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.status != 0:  # if account is not open, block update from client
            return Response('Account is not open, cannot update', status=status.HTTP_403_FORBIDDEN)
        kwargs['partial'] = True
        partial = kwargs.pop('partial', False)
        serializer = self.get_serializer_class()(data=request.data, partial=partial, context={'request': request})
        serializer.is_valid(raise_exception=True)
        updated = serializer.update(instance, serializer.validated_data)
        return Response(self.serializer_response_class(updated).data)

    @transaction.atomic
    def create_new_account(self, request):
        client = SupportRequest.target_user(self.request).client
        serializer = serializers.new_account_fabric(request.data)
        if serializer.is_valid():
            try:
                account = serializer.save(request, client)
            except ValidationError as e:
                return Response({'error': e.detail},
                                status=status.HTTP_400_BAD_REQUEST)
            return Response(self.serializer_response_class(instance=account).data)
        return Response({'error': serializer.errors},
                        status=status.HTTP_400_BAD_REQUEST)

    @list_route(methods=['POST'])
    def rollover(self, request):
        return self.create_new_account(request)

    @list_route(methods=['POST'])
    def trust(self, request):
        return self.create_new_account(request)

    @list_route(methods=['POST'])
    def joint(self, request):
        return self.create_new_account(request)

    @list_route(methods=['POST'], url_path='joint/resend-email')
    def joint_resend_email(self, request):
        client = SupportRequest.target_user(self.request).client
        account = ClientAccount.objects.get(primary_owner=client, account_type=constants.ACCOUNT_TYPE_JOINT)
        cosignee = account.signatories.first()
        jacm = JointAccountConfirmationModel.objects.get(account=account)
        context = RequestContext(request, {
            'site': get_current_site(request),
            'confirmation': jacm,
        })
        render = curry(render_to_string, context=context)
        cosignee.user.email_user(
            render('email/client/joint-confirm/subject.txt').strip(),
            message=render('email/client/joint-confirm/message.txt'),
            html_message=render('email/client/joint-confirm/message.html'),
        )
        return Response('ok', status=status.HTTP_200_OK)

    @detail_route(methods=['get', 'post'], url_path='beneficiaries')
    def beneficiaries(self, request, pk=None, **kwargs):
        instance = self.get_object()
        if instance.status != 0:  # if account is not open, block update from client
            return Response('Account is not open, cannot update', status=status.HTTP_403_FORBIDDEN)
        kwargs['partial'] = True
        partial = kwargs.pop('partial', False)
        if request.user != instance.primary_owner.user and request.user != instance.primary_owner.advisor.user:
            raise PermissionDenied()
        if request.method == 'POST':
            # create new beneficiary and add to account
            request.data['account'] = instance.id
            serializer = serializers.AccountBeneficiaryCreateSerializer(data=request.data, partial=partial, context={'request': request})
            serializer.is_valid(raise_exception=True)
            beneficiary = serializer.save()
            beneficiaries = AccountBeneficiary.objects.filter(account=instance)
            serializer = serializers.AccountBeneficiarySerializer(beneficiaries, many=True)
            return Response(serializer.data)
        beneficiaries = AccountBeneficiary.objects.filter(account=instance)
        serializer = serializers.AccountBeneficiarySerializer(beneficiaries, many=True)
        return Response(serializer.data)

    @detail_route(methods=['post'], url_path='close')
    def close(self, request, pk=None, **kwargs):
        instance = self.get_object()
        serializer = serializers.CloseAccountRequestSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        close_account = serializer.save()
        close_account.account.status = 1
        close_account.account.save()
        close_account.send_admin_email()
        # close choice check
        if close_account.close_choice == CloseAccountRequest.CloseChoice.liquidate.value:
            # email Advisor
            close_account.send_advisor_email()
        elif close_account.close_choice == CloseAccountRequest.CloseChoice.transfer_to_account.value:
            pass
        elif close_account.close_choice == CloseAccountRequest.CloseChoice.transfer_to_custodian.value:
            close_account.send_advisor_email()
        else:  # take direct custody
            close_account.send_advisor_email()
        return Response(serializer.data)

    @detail_route(methods=['post'], permission_classes=[IsAdvisorOrClient,], url_path='make-acats-transfer/')
    def make_acats_transfer(self, request, pk=None, *args, **kwargs):
        # TODO: Implement IB ACATS Transfer
        """
        request.data format
        {
            'broker_id': ...
            'broker_name': ...
            'src_ira_type': ...
            'signature': ...
        }
        """
        instance = self.get_object()
        client = instance.primary_owner
        if client.residential_address.region.country != 'US':
            raise exceptions.PermissionDenied('Only US clients can make ACATS transfer')

        return Response('ok')


class AccountBeneficiaryViewSet(ApiViewMixin,
                                NestedViewSetMixin,
                                mixins.UpdateModelMixin,
                                mixins.DestroyModelMixin,
                                viewsets.ReadOnlyModelViewSet):
    model = AccountBeneficiary
    queryset = AccountBeneficiary.objects.all()
    permission_classes = (IsAdvisorOrClient,)
    serializer_response_class = serializers.AccountBeneficiarySerializer

    def get_queryset(self):
        """
        Because this viewset can have a primary owner and signatories,
        we don't use the queryset parsing features from NestedViewSetMixin as
        it only allows looking at one field for the parent.
        :return:
        """
        qs = super(AccountBeneficiaryViewSet, self).get_queryset()

        # show "permissioned" records only
        user = SupportRequest.target_user(self.request)
        qs.filter(Q(account__primary_owner__user=user) | Q(account__primary_owner__advisor__user=user) )
        return qs

    def get_serializer_class(self):
        if self.request.method == 'PUT':
            return serializers.AccountBeneficiaryUpdateSerializer
        elif self.request.method == 'POST':
            return serializers.AccountBeneficiaryCreateSerializer
        else:
            # Default for get and other requests is the read only serializer
            return serializers.AccountBeneficiarySerializer

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if request.user != instance.account.primary_owner.user and request.user != instance.account.primary_owner.advisor.user:
            raise PermissionDenied()
        super(AccountBeneficiaryViewSet, self).destroy(request, *args, **kwargs)
        return Response('null', status=status.HTTP_200_OK)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if request.user != instance.account.primary_owner.user and request.user != instance.account.primary_owner.advisor.user:
            raise PermissionDenied()
        return super(AccountBeneficiaryViewSet, self).retrieve(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        kwargs['partial'] = True
        partial = kwargs.pop('partial', False)
        if request.user != instance.account.primary_owner.user and request.user != instance.account.primary_owner.advisor.user:
            raise PermissionDenied()
        serializer = self.get_serializer_class()(data=request.data, partial=partial, context={'account': instance.account, 'beneficiary': instance})
        serializer.is_valid(raise_exception=True)
        updated = serializer.update(instance, serializer.validated_data)
        return Response(self.serializer_response_class(updated).data)
