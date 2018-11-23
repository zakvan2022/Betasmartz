from api.v1.serializers import ReadOnlyModelSerializer
from django.db import transaction
from django.utils.translation import ugettext_lazy as _
from ..user.serializers import UserFieldSerializer
from api.v1.address.serializers import AddressSerializer, AddressUpdateSerializer, UNSET_ADDRESS
from firm.models import Firm, FirmConfig, FirmData, AuthorisedRepresentative, FirmEmailInvite
from multi_sites.models import AccountType, FiscalYear
from portfolios.models import get_default_set, PortfolioSet
from rest_framework import exceptions, serializers
from user.models import User
import logging


logger = logging.getLogger('api.v1.firm.serializers')
RESIDENTIAL_ADDRESS_KEY = 'residential_address'


class FirmConfigSerializer(ReadOnlyModelSerializer):
    class Meta:
        model = FirmConfig
        exclude = ('id', 'firm')


class FirmDataSerializer(ReadOnlyModelSerializer):
    class Meta:
        model = FirmData
        exclude = ('id', 'firm')


class FirmDataCreateSerializer(serializers.ModelSerializer):
    office_address = AddressUpdateSerializer(required=False)
    postal_address = AddressUpdateSerializer(required=False)
    class Meta:
        model = FirmData
        exclude = ('firm',)

    def create(self, validated_data):
        if 'office_address' in validated_data:
            office_address_ser = AddressUpdateSerializer(data=validated_data.pop('office_address'))
        else:
            office_address_ser = AddressUpdateSerializer(data=UNSET_ADDRESS)
        office_address_ser.is_valid(raise_exception=True)
        validated_data['office_address'] = office_address_ser.save()

        if 'postal_address' in validated_data:
            postal_address_ser = AddressUpdateSerializer(data=validated_data.pop('postal_address'))
        else:
            postal_address_ser = AddressUpdateSerializer(data=UNSET_ADDRESS)
        postal_address_ser.is_valid(raise_exception=True)
        validated_data['postal_address'] = postal_address_ser.save()

        return super(FirmDataCreateSerializer, self).create(validated_data)


class FirmConfigCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = FirmConfig
        exclude = ('firm',)


class FirmSerializer(ReadOnlyModelSerializer):
    config = FirmConfigSerializer()
    details = FirmDataSerializer()

    class Meta:
        model = Firm
        fields = (
            'id',
            'logo',
            'colored_logo',
            'name',
            'slug',
            'config',
            'details'
        )


class FirmCreateSerializer(serializers.ModelSerializer):
    """
    Create Serializer, POST requests only
    """
    details = FirmDataCreateSerializer(required=False)
    config = FirmConfigSerializer(required=False)
    default_portfolio_set = serializers.PrimaryKeyRelatedField(queryset=PortfolioSet.objects.all(),
                                                               required=False)
    fiscal_years = serializers.PrimaryKeyRelatedField(many=True,
                                                      queryset=FiscalYear.objects.all(),
                                                      required=False)
    account_types = serializers.PrimaryKeyRelatedField(many=True,
                                                       queryset=AccountType.objects.all(),
                                                       required=False)

    class Meta:
        model = Firm

    def set_default_values(self, data):
        if not 'default_portfolio_set' in data:
            data.setdefault('default_portfolio_set', get_default_set())
        if not 'fiscal_years' in data:
            data.setdefault('fiscal_years', FiscalYear.objects.all().values_list('id', flat=True))
        if not 'account_types' in data:
            data.setdefault('account_types', AccountType.objects.all().values_list('id', flat=True))
        return data

    @transaction.atomic
    def create(self, validated_data):
        data = self.set_default_values(validated_data)
        if 'details' in validated_data:
            details_ser = FirmDataCreateSerializer(data=validated_data.pop('details'))
        if 'config' in validated_data:
            config_ser = FirmConfigCreateSerializer(data=validated_data.pop('config'))

        firm = super(FirmCreateSerializer, self).create(data)

        if 'details_ser' in locals():
            details_ser.is_valid(raise_exception=True)
            details_ser.save(firm=firm)
        if 'config' in locals():
            config_ser.save(firm=firm)
        return firm


class FirmUpdateSerializer(serializers.ModelSerializer):
    config = FirmConfigSerializer()
    details = FirmDataSerializer()

    class Meta:
        model = Firm
        read_only_fields = ('id', 'slug',)
        fields = (
            'id',
            'logo',
            'colored_logo',
            'name',
            'slug',
            'config',
            'details',
        )


class AuthorisedRepresentativeSerializer(ReadOnlyModelSerializer):
    """
    Read Serializer, GET requests only
    """
    user = UserFieldSerializer()
    firm = FirmSerializer()
    residential_address = AddressSerializer()
    regional_data = serializers.JSONField()

    class Meta:
        model = AuthorisedRepresentative


class AuthorisedRepresentativeCreateSerializer(serializers.ModelSerializer):
    """
    Create Serializer, POST requests only
    """
    residential_address = AddressUpdateSerializer(required=False)
    regional_data = serializers.JSONField(required=False)
    firm = FirmCreateSerializer()

    class Meta:
        model = AuthorisedRepresentative
        fields = (
            'phone_num',
            'regional_data',
            RESIDENTIAL_ADDRESS_KEY,
            'betasmartz_agreement',
            'date_of_birth',
            'civil_status',
            'firm',
        )

    @transaction.atomic
    def create(self, validated_data):
        if RESIDENTIAL_ADDRESS_KEY in validated_data:
            address_ser = AddressUpdateSerializer(data=validated_data.pop(RESIDENTIAL_ADDRESS_KEY))
        else:
            address_ser = AddressUpdateSerializer(data=UNSET_ADDRESS)
        address_ser.is_valid(raise_exception=True)
        validated_data[RESIDENTIAL_ADDRESS_KEY] = address_ser.save()

        firm_ser = FirmCreateSerializer(data=validated_data.pop('firm'))
        firm_ser.is_valid(raise_exception=True)
        validated_data['firm'] = firm_ser.save()

        return super(AuthorisedRepresentativeCreateSerializer, self).create(validated_data)


class AuthorisedRepresentativeUpdateSerializer(serializers.ModelSerializer):
    """
    Update Serializer, PUT requests only
    """
    residential_address = AddressUpdateSerializer()
    regional_data = serializers.JSONField()
    firm = FirmUpdateSerializer()

    class Meta:
        model = AuthorisedRepresentative
        fields = (
            'phone_num',
            'regional_data',
            RESIDENTIAL_ADDRESS_KEY,
            'betasmartz_agreement',
            'date_of_birth',
            'civil_status',
            'firm',
        )


class FirmInvitationCreateSerializer(serializers.ModelSerializer):
    """
    This serializer is used to create FirmEmailInvite instance for firm onboarding
    by api/v1/firm/request-onboarding
    """

    class Meta:
        model = FirmEmailInvite
        fields = (
            'first_name',
            'last_name',
            'email',
            'phone_number'
        )

    def validate_email(self, email):
        if User.objects.filter(email=email).count() > 0:
            raise serializers.ValidationError('User already exists with this email')
        return email


class FirmInvitationSerializer(ReadOnlyModelSerializer):
    """
    A user in the middle of onboarding will use this
    serializer, pre-registration and non-authenticated
    """

    class Meta:
        model = FirmEmailInvite
        read_only_fields = (
            'email',
            'firm_agreement_url',
            'firm_onboarding_url',
            'invite_key',
            'status',
        )
        fields = (
            'email',
            'firm_agreement_url',
            'firm_onboarding_url',
            'first_name',
            'invite_key',
            'last_name',
            'middle_name',
            'phone_number',
            'status',
        )


class PrivateFirmInvitationSerializer(serializers.ModelSerializer):
    """
    Authenticated users will retrieve and update through this
    serializer.
    """
    onboarding_data = serializers.JSONField()

    class Meta:
        model = FirmEmailInvite
        read_only_fields = (
            'email',
            'firm_agreement_url',
            'firm_onboarding_url',
            'invite_key',
            'status',
        )
        fields = (
            'email',
            'firm_agreement_url',
            'firm_onboarding_url',
            'invite_key',
            'onboarding_data',
            'phone_number',
            'status',
        )


class FirmUserRegistrationSerializer(serializers.Serializer):
    """
    For POST request to register from an email token
    """
    invite_key = serializers.CharField(required=True)
    password = serializers.CharField(style={'input_type': 'password'})
    question_one = serializers.CharField(required=False)
    question_one_answer = serializers.CharField(required=False)
    question_two = serializers.CharField(required=False)
    question_two_answer = serializers.CharField(required=False)

    """
    These fields are optional, if not specified, defaults to invitation object
    Added these fields in case front-end onboarding makes modification to these fields
    """
    email = serializers.EmailField(required=False)
    first_name = serializers.CharField(required=False)
    middle_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False)

    def validate(self, attrs):
        invite_params = {
            'invite_key': attrs.get('invite_key'),
        }

        invite_lookup = FirmEmailInvite.objects.filter(**invite_params)

        if not invite_lookup.exists():
            msg = _('Invalid invitation key')
            raise exceptions.ValidationError(msg)

        self.invite = invite_lookup.get()

        email = attrs['email'] if 'email' in attrs else self.invite.email
        if User.objects.filter(email=email).exists():
            msg = _('Email is already in use')
            raise exceptions.ValidationError(msg)
        attrs['email'] = email

        if not 'first_name' in attrs:
            attrs['first_name'] = self.invite.first_name

        if not 'middle_name' in attrs:
            attrs['middle_name'] = self.invite.middle_name

        if not 'last_name' in attrs:
            attrs['last_name'] = self.invite.last_name

        if self.invite.status == FirmEmailInvite.STATUS_CREATED:
            msg = _('Unable to accept this invitation, it hasnt been sent yet')
            raise exceptions.ValidationError(msg)

        if self.invite.status == FirmEmailInvite.STATUS_ACCEPTED:
            msg = _('Unable to accept this invitation, it has already been accepted')
            raise exceptions.ValidationError(msg)

        if self.invite.status == FirmEmailInvite.STATUS_EXPIRED:
            self.invite.advisor.user.email_user('A client tried to use an expired invitation'
                    "Your client %s %s (%s) just tried to register using an invite "
                    "you sent them, but it has expired!"%
                    (self.invite.first_name, self.invite.last_name, self.invite.email))
            msg = _('Unable to accept this invitation, it has expired')
            raise exceptions.ValidationError(msg)

        if self.invite.status == FirmEmailInvite.STATUS_COMPLETE:
            msg = _('Unable to accept this invitation, it has already been completed')
            raise exceptions.ValidationError(msg)

        if 'question_one' in attrs:
            if 'question_one_answer' not in attrs or not attrs['question_one_answer']:
                msg = _('Security question one answer is required')
                raise exceptions.ValidationError(msg)

        if 'question_two' in attrs:
            if 'question_two_answer' not in attrs or not attrs['question_two_answer']:
                msg = _('Security question two answer is required')
                raise exceptions.ValidationError(msg)

        return attrs
