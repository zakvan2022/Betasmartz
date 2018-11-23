import logging

from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.template import RequestContext
from django.template.loader import render_to_string
from django.utils.functional import curry
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from api.v1.serializers import (NoCreateModelSerializer,
                                NoUpdateModelSerializer,
                                ReadOnlyModelSerializer)
from client.models import AccountBeneficiary, Client, ClientAccount, \
    CloseAccountRequest, JointAccountConfirmationModel
from main import constants

from brokers.interactive_brokers.onboarding import onboarding as onb
from user.models import SecurityAnswer

logger = logging.getLogger('api.v1.account.serializers')


class AccountBeneficiarySerializer(ReadOnlyModelSerializer):
    class Meta:
        model = AccountBeneficiary


class AccountBeneficiaryUpdateSerializer(serializers.ModelSerializer):
    """
    For PUT update requests
    """
    class Meta:
        model = AccountBeneficiary
        fields = (
            'type',
            'name',
            'relationship',
            'birthdate',
            'share',
        )

    def validate(self, data):
        account = self.context.get('account')
        beneficiary = self.context.get('beneficiary')
        if 'type' in data:
            beneficiaries = AccountBeneficiary.objects.filter(account=account, type=data['type'])
        else:
            beneficiaries = AccountBeneficiary.objects.filter(account=account, type=beneficiary.type)
        shares = [b.share for b in beneficiaries if b.id != beneficiary.id]
        shares.append(data['share'])
        if sum(shares) > 1.0:
            raise serializers.ValidationError({'share': 'Beneficiaries for account would be over 100%'})
        return data


class AccountBeneficiaryCreateSerializer(serializers.ModelSerializer):
    """
    For POST create requests
    """
    class Meta:
        model = AccountBeneficiary
        fields = (
            'type',
            'name',
            'relationship',
            'birthdate',
            'share',
            'account',
        )

    def validate(self, data):
        beneficiaries = AccountBeneficiary.objects.filter(account=data['account'], type=data['type'])
        shares = [b.share for b in beneficiaries]
        shares.append(data['share'])
        if sum(shares) > 1.0:
            raise serializers.ValidationError({'share': 'Beneficiaries for account would be over 100%'})
        return data


class ClientAccountSerializer(ReadOnlyModelSerializer):
    """
    Read-only ClientAccount Serializer
    """
    ib_account = serializers.CharField(max_length=32, source='ib_account.ib_account')
    class Meta:
        model = ClientAccount


class ClientAccountCreateSerializer(NoUpdateModelSerializer):
    """
    When creating an account via the API, we want the name to be required,
    so enforce it.
    """
    account_name = serializers.CharField(max_length=255, required=True)

    class Meta:
        model = ClientAccount
        fields = (
            'account_type',
            'account_name',
            'account_number',
            'primary_owner',
        )

    def create(self, validated_data):
        ps = validated_data['primary_owner'].advisor.default_portfolio_set
        validated_data.update({
            'default_portfolio_set': ps,
        })
        return (super(ClientAccountCreateSerializer, self)
                .create(validated_data))


class ClientAccountUpdateSerializer(NoCreateModelSerializer):
    """
    Updatable ClientAccount Serializer
    """
    question_one = serializers.IntegerField(required=True)
    answer_one = serializers.CharField(required=True)
    question_two = serializers.IntegerField(required=True)
    answer_two = serializers.CharField(required=True)

    class Meta:
        model = ClientAccount
        fields = (
            'account_name',
            'tax_loss_harvesting_consent',
            'tax_loss_harvesting_status',

            'question_one',
            'answer_one',
            'question_two',
            'answer_two',
        )

    def validate(self, data):
        request = self.context.get('request')
        user = request.user
        # no user is create request for initial registration

        # SecurityAnswer checks
        if data.get('question_one') == data.get('question_two'):
            logger.error('ClientAccountUpdateSerializer given matching questions %s' % data.get('question_one'))
            raise serializers.ValidationError({'question_two': 'Questions must be unique'})

        try:
            sa1 = SecurityAnswer.objects.get(pk=data.get('question_one'))
            if sa1.user != user:
                logger.error('SecurityAnswer not found for user %s and question %s with ClientAccountUpdateSerializer' % (user.email, data.get('question_one')))
                raise serializers.ValidationError({'question_one': 'User does not own given question'})
        except:
            logger.error('ClientAccountUpdateSerializer question %s not found' % data.get('question_one'))
            raise serializers.ValidationError({'question_one': 'Question not found'})

        if not sa1.check_answer(data.get('answer_one')):
            logger.error('ClientAccountUpdateSerializer answer two was wrong')
            raise serializers.ValidationError({'answer_one': 'Wrong answer'})

        try:
            sa2 = SecurityAnswer.objects.get(pk=data.get('question_two'))
            if sa2.user != user:
                logger.error('SecurityAnswer not found for user %s and question %s with ClientAccountUpdateSerializer' % (user.email, data.get('question_two')))
                raise serializers.ValidationError({'question_two': 'User does not own given question'})
        except:
            logger.error('ClientAccountUpdateSerializer question %s not found' % data.get('question_two'))
            raise serializers.ValidationError({'question_two': 'Question not found'})

        if not sa2.check_answer(data.get('answer_two')):
            logger.error('ClientAccountUpdateSerializer answer two was wrong')
            raise serializers.ValidationError({'answer_two': 'Wrong answer'})

        return data


class CloseAccountRequestSerializer(serializers.ModelSerializer):

    class Meta:
        model = CloseAccountRequest
        fields = ('account', 'close_choice', 'account_transfer_form')

    def validate(self, data):
        request = self.context.get('request')
        user = request.user
        account_ids = [a.id for a in ClientAccount.objects.filter(primary_owner__user=user)]
        if data['account'].id not in account_ids:
            raise serializers.ValidationError({'account': 'User does not own account'})
        if data['close_choice'] == 1:
            # internal transfer needs pdf
            if 'account_transfer_form' not in data:
                raise serializers.ValidationError({'account_transfer_form': 'Account transfer form pdf file required for account transfer'})
        return data


class NewAccountFabricBase(serializers.Serializer):
    def save(self, request, client) -> ClientAccount:
        raise NotImplementedError()


def new_account_fabric(data: dict) -> NewAccountFabricBase:
    account_serializers = {
        JointAccountConfirmation: [constants.ACCOUNT_TYPE_JOINT],
        AddTrustAccount: [constants.ACCOUNT_TYPE_TRUST],
        AddRolloverAccount: [
            constants.ACCOUNT_TYPE_401K,
            constants.ACCOUNT_TYPE_ROTH401K,
            constants.ACCOUNT_TYPE_IRA,
            constants.ACCOUNT_TYPE_ROTHIRA,
            constants.ACCOUNT_TYPE_SEPIRA,
            constants.ACCOUNT_TYPE_SIMPLEIRA,
            constants.ACCOUNT_TYPE_403B,
            constants.ACCOUNT_TYPE_PENSION,
            constants.ACCOUNT_TYPE_401A,
            constants.ACCOUNT_TYPE_457,
            constants.ACCOUNT_TYPE_PROFITSHARING,
            constants.ACCOUNT_TYPE_THRIFTSAVING,
        ],
    }
    try:
        at = data['account_type']
        for klass, types in account_serializers.items():
            if at in types:
                return klass(data=data)
    except KeyError:
        pass
    raise ValidationError({'account_type': 'Invalid account type.'})


class AddRolloverAccount(NewAccountFabricBase):
    provider = serializers.CharField()
    account_type = serializers.ChoiceField(choices=constants.ACCOUNT_TYPES)
    account_number = serializers.CharField()
    amount = serializers.FloatField()
    signature = serializers.CharField()

    def save(self, request, client):
        data = self.validated_data
        account_type = data['account_type']
        if client.primary_accounts.filter(account_type=account_type).exists():
            raise ValidationError('Only one Rollover account can be created.')
        account = ClientAccount.objects.create(
            account_type=account_type,
            account_name=dict(constants.ACCOUNT_TYPES)[account_type],
            account_number=data['account_number'],
            primary_owner=client,
            default_portfolio_set=client.advisor.default_portfolio_set,
            confirmed=account_type in settings.AUTOCONFIRMED_ACCOUNTS,
        )
        # TODO save source account rollover data
        return account


class AddTrustAccount(NewAccountFabricBase):
    trust_legal_name = serializers.CharField()
    trust_nickname = serializers.CharField()
    trust_state = serializers.CharField()
    establish_date = serializers.DateField()
    ein = serializers.CharField(required=False, allow_blank=True)
    ssn = serializers.CharField(required=False, allow_blank=True)
    address = serializers.CharField()
    city = serializers.CharField()
    state = serializers.CharField()
    zip = serializers.CharField()

    def validate(self, attrs):
        ein = attrs.get('ein', None)
        ssn = attrs.get('ssn', None)
        if not (ein or ssn):
            raise ValidationError({
                'ein': 'Either EIN or SSN must present.',
                'ssn': 'Either EIN or SSN must present.',
            })
        if ein and ssn:
            raise ValidationError({
                'ein': 'Only EIN or SSN must present.',
                'ssn': 'Only EIN or SSN must present.',
            })
        return attrs

    def save(self, request, client):
        data = self.validated_data
        account_type = constants.ACCOUNT_TYPE_TRUST
        if client.primary_accounts.filter(account_type=account_type).exists():
            raise ValidationError('Only one Trust account can be created.')
        account = ClientAccount.objects.create(
            account_type=account_type,
            account_name=data['trust_nickname'],
            primary_owner=client,
            default_portfolio_set=client.advisor.default_portfolio_set,
            confirmed=account_type in settings.AUTOCONFIRMED_ACCOUNTS,
        )
        # todo save trust info
        return account


class JointAccountConfirmation(NewAccountFabricBase):
    email = serializers.EmailField()
    ssn = serializers.CharField()

    client = None

    def validate(self, attrs):
        try:
            self.client = Client.objects.get(user__email=attrs['email'])
            if self.client.regional_data.get('ssn', '') != attrs['ssn']:
                raise ValueError
        except (Client.DoesNotExist, TypeError, KeyError, ValueError):
            raise ValidationError({'email': 'User cannot be found.'})
        return attrs

    def save(self, request, client):
        cosignee = self.client
        existing_accounts = ClientAccount.objects.filter(
            Q(primary_owner=client) | Q(primary_owner=cosignee),
            Q(signatories__in=[client]) | Q(signatories__in=[cosignee]),
            account_type=constants.ACCOUNT_TYPE_JOINT,
        )
        if existing_accounts:
            raise ValidationError({
                'account_type': 'Only one joint account allowed.'
            })
        account = ClientAccount.objects.create(
            account_type=constants.ACCOUNT_TYPE_JOINT,
            account_name='JOINT',
            primary_owner=client,
            default_portfolio_set=client.advisor.default_portfolio_set,
        )
        account.signatories = [cosignee]
        account.save()
        jacm = JointAccountConfirmationModel.objects.create(
            primary_owner=client,
            cosignee=cosignee,
            account=account,
        )

        context = RequestContext(request, {
            'site': get_current_site(request),
            'confirmation': jacm,
            'confirm_url': '{}{}'.format(settings.SITE_URL,
                                         reverse('confirm-joint-account', kwargs={ 'token': jacm.token })),
            'firm': jacm.cosignee.firm
        })
        render = curry(render_to_string, context=context)
        cosignee.user.email_user(
            render('email/client/joint-confirm/subject.txt').strip(),
            message=render('email/client/joint-confirm/message.txt'),
            html_message=render('email/client/joint-confirm/message.html'),
        )
        # connect IB broker onboarding ftp
        primary_ib_onboard = client.ib_onboard
        primary_ib_onboard.account_type = constants.ACCOUNT_TYPE_JOINT
        primary_ib_onboard.joint_type = request.data['joint_type']
        cosignee_ib_onboard = cosignee.ib_onboard
        cosignee_ib_onboard.account_type = constants.ACCOUNT_TYPE_JOINT
        cosignee_ib_onboard.joint_type = request.data['joint_type']
        status = onb.onboard('JOINT', primary_ib_onboard, cosignee_ib_onboard)

        return account
