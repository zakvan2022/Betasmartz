from api.v1.serializers import ReadOnlyModelSerializer
from api.v1.user.serializers import UserFieldSerializer
from api.v1.address.serializers import AddressUpdateSerializer, UNSET_ADDRESS
from advisor.models import Advisor
from rest_framework import serializers
from user.models import User


class AdvisorSerializer(ReadOnlyModelSerializer):
    class Meta:
        model = Advisor
        exclude = (
            'user',
            'confirmation_key',
            'letter_of_authority',
            'betasmartz_agreement',
        )


class AdvisorFieldSerializer(ReadOnlyModelSerializer):
    user = UserFieldSerializer()

    class Meta:
        model = Advisor
        fields = (
            'id',
            'gender',
            'work_phone_num',
            'user',
            'firm',
            'email'
        )


class AdvisorCreateSerializer(serializers.ModelSerializer):
    residential_address = AddressUpdateSerializer()

    class Meta:
        model = Advisor
        fields = (
            'firm',
            'residential_address',
            'work_phone_num',
        )

    def create(self, validated_data):
        if 'residential_address' in validated_data:
            address_ser = AddressUpdateSerializer(data=validated_data.pop('residential_address'))
        else:
            address_ser = AddressUpdateSerializer(data=UNSET_ADDRESS)
        address_ser.is_valid(raise_exception=True)
        validated_data['residential_address'] = address_ser.save()

        return super(AdvisorCreateSerializer, self).create(validated_data)


class AdvisorUserCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            'first_name',
            'last_name',
            'email',
            'password'
        )
