import logging
import uuid

from django.db import transaction
from django.utils.translation import ugettext_lazy as _
from rest_framework import exceptions, serializers

from api.v1.address.serializers import AddressSerializer, AddressUpdateSerializer, UNSET_ADDRESS
from api.v1.advisor.serializers import AdvisorFieldSerializer
from api.v1.serializers import ReadOnlyModelSerializer
from api.v1.firm.serializers import FirmConfigSerializer
from api.v1.validation.serializers import PhoneNumberValidationSerializer
from client.models import AccountTypeRiskProfileGroup, Client, EmailInvite, \
    EmailNotificationPrefs, HealthDevice, IBAccount, IBOnboard, RiskProfileAnswer, \
    RiskProfileGroup, ExternalAsset, ExternalAssetTransfer
from main import constants
from main.constants import ACCOUNT_TYPE_PERSONAL
from user.models import User
from pdf_parsers.tax_return import parse_pdf as parse_tax_pdf
from pdf_parsers.social_security import parse_pdf as parse_ss_pdf
from user.models import SecurityAnswer
from ..user.serializers import UserFieldSerializer
from django.conf import settings
from brokers.interactive_brokers.onboarding import onboarding

logger = logging.getLogger('api.v1.client.serializers')
RESIDENTIAL_ADDRESS_KEY = 'residential_address'


class HealthDeviceSerializer(ReadOnlyModelSerializer):
    # id = serializers.IntegerField(source='health_device.id', read_only=True)
    # provider = serializers.IntegerField(source='health_device.provider', read_only=True)
    # expires_at = serializers.DateTimeField(source='health_device.expires_at', read_only=True)

    class Meta:
        model = HealthDevice
        fields = ('id', 'provider', 'expires_at')


class IBOnboardSerializer(ReadOnlyModelSerializer):
    """
    For Update (GET) requests only
    """
    employer_address = AddressSerializer()
    tax_address = AddressSerializer()

    class Meta:
        model = IBOnboard


class IBOnboardCreateSerializer(serializers.ModelSerializer):
    """
    For Update (POST) requests only
    """
    employer_address = AddressUpdateSerializer(required=False)
    tax_address = AddressUpdateSerializer(required=False)

    class Meta:
        model = IBOnboard
        fields = '__all__'

    def create(self, validated_data):
        if 'employer_address' in validated_data:
            employer_address_ser = AddressUpdateSerializer(data=validated_data.pop('employer_address'))
            employer_address_ser.is_valid(raise_exception=True)
            validated_data['employer_address'] = employer_address_ser.save()

        if 'tax_address' in validated_data:
            tax_address_ser = AddressUpdateSerializer(data=validated_data.pop('tax_address'))
            tax_address_ser.is_valid(raise_exception=True)
            validated_data['tax_address'] = tax_address_ser.save()

        ib_onboard = super(IBOnboardCreateSerializer, self).create(validated_data)
        return ib_onboard


class ClientSerializer(ReadOnlyModelSerializer):
    user = UserFieldSerializer()
    advisor = AdvisorFieldSerializer()
    residential_address = AddressSerializer()
    regional_data = serializers.JSONField()
    reason = serializers.SerializerMethodField()
    health_device = serializers.SerializerMethodField()
    ib_onboard = IBOnboardSerializer()

    class Meta:
        model = Client

    def get_reason(self, obj):
        if hasattr(obj.user, 'invitation'):
            return obj.user.invitation.reason
        return None

    def get_health_device(self, obj):
        if hasattr(obj, 'health_device'):
            return HealthDeviceSerializer(obj.health_device).data
        return None


class ClientFieldSerializer(ReadOnlyModelSerializer):
    residential_address = AddressSerializer()
    advisor = AdvisorFieldSerializer()
    regional_data = serializers.JSONField()
    reason = serializers.SerializerMethodField()

    class Meta:
        model = Client
        exclude = (
            'user',
            'client_agreement',
            'confirmation_key',
            'create_date',
        )

    def get_reason(self, obj):
        if hasattr(obj.user, 'invitation'):
            return obj.user.invitation.reason
        return None


class ClientCreateSerializer(serializers.ModelSerializer):
    """
    For Create POST requests only
    """
    qs = RiskProfileAnswer.objects.all()
    risk_profile_responses = serializers.PrimaryKeyRelatedField(many=True,
                                                                queryset=qs,
                                                                required=False)
    residential_address = AddressUpdateSerializer(required=False)
    regional_data = serializers.JSONField()
    ib_onboard = IBOnboardCreateSerializer(required=False)

    class Meta:
        model = Client
        fields = (
            'employment_status',
            RESIDENTIAL_ADDRESS_KEY,
            'income',
            'other_income',
            'occupation',
            'industry_sector',
            'employer_type',
            'student_loan',
            'student_loan_assistance_program',
            'student_loan_graduate_looking',
            'student_loan_parent_looking',
            'hsa_eligible',
            'hsa_provider_name',
            'hsa_state',
            'hsa_coverage_type',
            'employer',
            'civil_status',
            'risk_profile_responses',
            'betasmartz_agreement',
            'advisor_agreement',
            'politically_exposed',
            'phone_num',
            'regional_data',
            'smoker',
            'daily_exercise',
            'weight',
            'height',
            'drinks',
            'date_of_birth',
            'gender',
            'ib_onboard',
        )

    def validate_phone_num(self, phone_num):
        serializer = PhoneNumberValidationSerializer(data={'number': phone_num})
        if not serializer.is_valid():
            raise serializers.ValidationError('Invalid phone number')
        return serializer.validated_data['number']

    @transaction.atomic
    def create(self, validated_data):
        # Default to Personal account type for risk profile group on a brand
        # new client (since they have no accounts yet, we have to assume)
        rpg = RiskProfileGroup.objects.get(account_types__account_type=constants.ACCOUNT_TYPE_PERSONAL)
        validated_data['risk_profile_group'] = rpg
        if RESIDENTIAL_ADDRESS_KEY in validated_data:
            address_ser = AddressUpdateSerializer(data=validated_data.pop(RESIDENTIAL_ADDRESS_KEY))
        else:
            address_ser = AddressUpdateSerializer(data=UNSET_ADDRESS)
        address_ser.is_valid(raise_exception=True)
        validated_data[RESIDENTIAL_ADDRESS_KEY] = address_ser.save()

        if 'ib_onboard' in validated_data:
            ib_onboard_ser = IBOnboardCreateSerializer(data=validated_data.pop('ib_onboard'))
            ib_onboard_ser.is_valid(raise_exception=True)

        # For now we auto confirm and approve the client.
        validated_data['is_confirmed'] = True
        validated_data['is_accepted'] = True

        client = super(ClientCreateSerializer, self).create(validated_data)
        client_account = client.primary_accounts.create(
            account_type=constants.ACCOUNT_TYPE_PERSONAL,
            default_portfolio_set=validated_data['advisor'].default_portfolio_set,
            confirmed=True,
        )

        if 'ib_onboard_ser' in locals():
            ib_onboard = ib_onboard_ser.save(client=client)
            if ib_onboard.account_number is not None: # If the client already has IB account create and link IBAccount object
                ib_account = IBAccount(bs_account=client_account, ib_account=ib_onboard.account_number)
                ib_account.save()
            else:
                # connect IB broker onboarding ftp
                status = onboarding.onboard('INDIVIDUAL', ib_onboard)

        return client


class ClientUpdateSerializer(serializers.ModelSerializer):
    """
    Write PUT update requests only
    """
    qs = RiskProfileAnswer.objects.all()
    risk_profile_responses = serializers.PrimaryKeyRelatedField(many=True,
                                                                queryset=qs,
                                                                required=False)
    residential_address = AddressUpdateSerializer()
    regional_data = serializers.JSONField()

    question_one = serializers.IntegerField(required=True)
    answer_one = serializers.CharField(required=True)
    question_two = serializers.IntegerField(required=True)
    answer_two = serializers.CharField(required=True)

    class Meta:
        model = Client
        fields = (
            'employment_status',
            RESIDENTIAL_ADDRESS_KEY,
            'income',
            'other_income',
            'occupation',
            'industry_sector',
            'employer_type',
            'student_loan',
            'employer',
            'civil_status',
            'risk_profile_responses',
            'betasmartz_agreement',
            'advisor_agreement',
            'phone_num',
            'regional_data',
            'smoker',
            'daily_exercise',
            'weight',
            'height',
            'drinks',
            'date_of_birth',
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
            logger.error('ClientUpdateSerializer given matching questions %s' % data.get('question_one'))
            raise serializers.ValidationError({'question_two': 'Questions must be unique'})

        try:
            sa1 = SecurityAnswer.objects.get(pk=data.get('question_one'))
            if sa1.user != user:
                logger.error('SecurityAnswer not found for user %s and question %s with ClientUpdateSerializer' % (user.email, data.get('question_one')))
                raise serializers.ValidationError({'question_one': 'User does not own given question'})
        except:
            logger.error('ClientUpdateSerializer question %s not found' % data.get('question_one'))
            raise serializers.ValidationError({'question_one': 'Question not found'})

        if not sa1.check_answer(data.get('answer_one')):
            logger.error('ClientUpdateSerializer answer two was wrong')
            raise serializers.ValidationError({'answer_one': 'Wrong answer'})

        try:
            sa2 = SecurityAnswer.objects.get(pk=data.get('question_two'))
            if sa2.user != user:
                logger.error('SecurityAnswer not found for user %s and question %s with ClientUpdateSerializer' % (user.email, data.get('question_two')))
                raise serializers.ValidationError({'question_two': 'User does not own given question'})
        except:
            logger.error('ClientUpdateSerializer question %s not found' % data.get('question_two'))
            raise serializers.ValidationError({'question_two': 'Question not found'})

        if not sa2.check_answer(data.get('answer_two')):
            logger.error('ClientUpdateSerializer answer two was wrong')
            raise serializers.ValidationError({'answer_two': 'Wrong answer'})

        return data

    def validate_phone_num(self, phone_num):
        serializer = PhoneNumberValidationSerializer(data={'number': phone_num})
        if not serializer.is_valid():
            raise serializers.ValidationError('Invalid phone number')
        return serializer.validated_data['number']

    def update(self, instance, validated_data):
        add_data = validated_data.pop(RESIDENTIAL_ADDRESS_KEY, None)
        if add_data is not None:
            address_ser = AddressUpdateSerializer(data=add_data)
            address_ser.is_valid(raise_exception=True)
            validated_data[RESIDENTIAL_ADDRESS_KEY] = address_ser.save()

        return super(ClientUpdateSerializer, self).update(instance, validated_data)


class EATransferPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExternalAssetTransfer
        exclude = ('asset',)


class EAWritableTransferPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExternalAssetTransfer
        fields = (
            'begin_date',
            'amount',
            'growth',
            'schedule',
        )


class ExternalAssetSerializer(ReadOnlyModelSerializer):
    transfer_plan = EATransferPlanSerializer()

    class Meta:
        model = ExternalAsset


class ExternalAssetWritableSerializer(serializers.ModelSerializer):
    # For the reverse relation.
    transfer_plan = EAWritableTransferPlanSerializer(required=False)

    class Meta:
        model = ExternalAsset
        fields = (
            'type',
            'name',
            'owner',
            'description',
            'valuation',
            'valuation_date',
            'growth',
            'acquisition_date',
            'debt',
            'transfer_plan',
        )

    def __init__(self, *args, **kwargs):
        super(ExternalAssetWritableSerializer, self).__init__(*args, **kwargs)
        request = self.context.get('request')
        if request.method == 'PUT':
            for field in self.fields.values():
                field.required = False

    @transaction.atomic
    def update(self, instance, validated_data):
        txp = validated_data.pop('transfer_plan', None)
        if txp:
            if instance.transfer_plan is not None:
                instance.transfer_plan.delete()
            ser = EAWritableTransferPlanSerializer(data=txp)
            ser.is_valid(raise_exception=True)
            ser.save(asset=instance)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

    @transaction.atomic
    def create(self, validated_data):
        txp = validated_data.pop('transfer_plan', None)
        instance = ExternalAsset.objects.create(**validated_data)
        if txp:
            ser = EAWritableTransferPlanSerializer(data=txp)
            ser.is_valid(raise_exception=True)
            ser.save(asset=instance)
        return instance


class InvitationSerializer(ReadOnlyModelSerializer):
    """
    A user in the middle of onboarding will use this
    serializer, pre-registration and non-authenticated
    """
    firm_name = serializers.SerializerMethodField()
    firm_logo = serializers.SerializerMethodField()
    firm_colored_logo = serializers.SerializerMethodField()
    client_agreement_url = serializers.SerializerMethodField()
    firm_config = serializers.SerializerMethodField()

    class Meta:
        model = EmailInvite
        read_only_fields = ('invite_key', 'email', 'client_agreement_url', 'salutation', 'suffix', 'firm_config')
        fields = (
            'invite_key',
            'status',
            'first_name',
            'middle_name',
            'last_name',
            'reason',
            'advisor',
            'firm_name',
            'firm_logo',
            'firm_colored_logo',
            'firm_config',
            'client_agreement_url',
            'email',
            'salutation',
            'suffix',
            'risk_score',
            'ib_account_number'
        )

    def get_firm_name(self, obj):
        return obj.advisor.firm.name

    def get_firm_logo(self, obj):
        return obj.advisor.firm.white_logo

    def get_firm_colored_logo(self, obj):
        return obj.advisor.firm.colored_logo

    def get_client_agreement_url(self, obj):
        cau = obj.advisor.firm.client_agreement_url
        return settings.SITE_URL + cau.url if cau else None

    def get_firm_config(self, obj):
        serializer = FirmConfigSerializer(obj.advisor.firm.config)
        return serializer.data


class PrivateInvitationSerializer(serializers.ModelSerializer):
    """
    Authenticated users will retrieve and update through this
    serializer.
    """
    # Includes onboarding data
    # Allows POST for registered users
    onboarding_data = serializers.JSONField()
    risk_profile_group = serializers.SerializerMethodField()
    firm_name = serializers.SerializerMethodField()
    firm_logo = serializers.SerializerMethodField()
    client_agreement_url = serializers.SerializerMethodField()
    firm_colored_logo = serializers.SerializerMethodField()
    tax_transcript_data = serializers.SerializerMethodField()
    social_security_statement_data = serializers.SerializerMethodField()
    partner_social_security_statement_data = serializers.SerializerMethodField()
    firm_config = serializers.SerializerMethodField()

    class Meta:
        model = EmailInvite
        read_only_fields = ('invite_key', 'email', 'status', 'client_agreement_url', 'salutation', 'invitation', 'firm_config', )
        fields = (
            'email',
            'invite_key',
            'status',
            'onboarding_data',
            'risk_profile_group',
            'reason',
            'advisor',
            'firm_name',
            'firm_logo',
            'firm_config',
            'client_agreement_url',
            'firm_colored_logo',
            'tax_transcript',
            'tax_transcript_data',  # this will be stored to client.region_data.tax_transcript_data
            'social_security_statement',
            'social_security_statement_data',
            'partner_social_security_statement',
            'partner_social_security_statement_data',
            'salutation',
            'suffix',
            'photo_verification',
            'risk_score',
            'ib_account_number'
        )

    def get_risk_profile_group(self, obj):
        return AccountTypeRiskProfileGroup.objects.get(account_type=ACCOUNT_TYPE_PERSONAL).id

    def get_firm_name(self, obj):
        return obj.advisor.firm.name

    def get_firm_logo(self, obj):
        return obj.advisor.firm.white_logo

    def get_firm_colored_logo(self, obj):
        return obj.advisor.firm.colored_logo

    def get_firm_config(self, obj):
        serializer = FirmConfigSerializer(obj.advisor.firm.config)
        return serializer.data

    def get_client_agreement_url(self, obj):
        cau = obj.advisor.firm.client_agreement_url
        return settings.SITE_URL + cau.url if cau else None

    def get_tax_transcript_data(self, obj):
        # parse_pdf
        if obj.tax_transcript:
            # save to tmp file to pass to parse_pdf
            # TODO: parse_pdf using subprocess file status command
            # to detect pdf_fonts, need to replace that with
            # something we can pass the in-memory file data here
            tmp_filename = '/tmp/' + str(uuid.uuid4()) + '.pdf'
            with open(tmp_filename, 'wb+') as f:
                for chunk in obj.tax_transcript.chunks():
                    f.write(chunk)
            obj.tax_transcript_data = parse_tax_pdf(tmp_filename)
            return obj.tax_transcript_data
        return None

    def get_social_security_statement_data(self, obj):
        if obj.social_security_statement:
            tmp_filename = '/tmp/' + str(uuid.uuid4()) + '.pdf'
            with open(tmp_filename, 'wb+') as f:
                for chunk in obj.social_security_statement.chunks():
                    f.write(chunk)
            obj.social_security_statement_data = parse_ss_pdf(tmp_filename)
            return obj.social_security_statement_data
        return None

    def get_partner_social_security_statement_data(self, obj):
        if obj.partner_social_security_statement:
            tmp_filename = '/tmp/' + str(uuid.uuid4()) + '.pdf'
            with open(tmp_filename, 'wb+') as f:
                for chunk in obj.partner_social_security_statement.chunks():
                    f.write(chunk)
            obj.partner_social_security_statement_data = parse_ss_pdf(tmp_filename)
            return obj.partner_social_security_statement_data
        return None


class ClientUserRegistrationSerializer(serializers.Serializer):
    """
    For POST request to register from an email token
    """
    invite_key = serializers.CharField(required=True)
    password = serializers.CharField(style={'input_type': 'password'})
    question_one = serializers.CharField(required=True)
    question_one_answer = serializers.CharField(required=True)
    question_two = serializers.CharField(required=True)
    question_two_answer = serializers.CharField(required=True)

    def validate(self, attrs):
        invite_params = {
            'invite_key': attrs.get('invite_key'),
        }

        invite_lookup = EmailInvite.objects.filter(**invite_params)

        if not invite_lookup.exists():
            msg = _('Invalid invitation key')
            raise exceptions.ValidationError(msg)

        self.invite = invite_lookup.get()

        if User.objects.filter(email=self.invite.email).exists():
            msg = _('Email is already in use')
            raise exceptions.ValidationError(msg)

        attrs['email'] = self.invite.email

        if self.invite.status == EmailInvite.STATUS_CREATED:
            msg = _('Unable to accept this invitation, it hasnt been sent yet')
            raise exceptions.ValidationError(msg)

        if self.invite.status == EmailInvite.STATUS_ACCEPTED:
            msg = _('Unable to accept this invitation, it has already been accepted')
            raise exceptions.ValidationError(msg)

        if self.invite.status == EmailInvite.STATUS_EXPIRED:
            self.invite.advisor.user.email_user('A client tried to use an expired invitation'
                    "Your client %s %s (%s) just tried to register using an invite "
                    "you sent them, but it has expired!"%
                    (self.invite.first_name, self.invite.last_name, self.invite.email))
            msg = _('Unable to accept this invitation, it has expired')
            raise exceptions.ValidationError(msg)

        if self.invite.status == EmailInvite.STATUS_COMPLETE:
            msg = _('Unable to accept this invitation, it has already been completed')
            raise exceptions.ValidationError(msg)

        return attrs


class EmailNotificationsSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailNotificationPrefs
        exclude = 'id', 'client',


class PersonalInfoSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    middle_name = serializers.CharField(source='user.middle_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    address = serializers.CharField(source='residential_address.address', required=False)
    phone = serializers.CharField(source='phone_num', required=False)

    class Meta:
        model = Client
        fields = ('first_name', 'middle_name', 'last_name', 'address', 'phone',
                  'employment_status', 'occupation', 'industry_sector', 'employer',
                  'income', 'other_income', 'net_worth')

    def save(self, **kwargs):
        new_address = self.validated_data.pop('residential_address', None)
        client = self.instance # client.Client
        if new_address:
            current_address = client.residential_address
            current_address.address = new_address['address']
            current_address.save(update_fields=['address'])
        instance = super(PersonalInfoSerializer, self).save(**kwargs)

        # TODO generate a new SOA

        return instance


class RiskProfileResponsesSerializer(serializers.ModelSerializer):
    qs = RiskProfileAnswer.objects.all()
    risk_profile_responses = serializers.PrimaryKeyRelatedField(many=True,
                                                                queryset=qs,
                                                                required=False)
    class Meta:
        model = Client
        fields = ('risk_profile_responses',)
