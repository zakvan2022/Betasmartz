from rest_framework import serializers
from execution.models import Order, ETNALogin, LoginResult, AccountId, Security


class ResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoginResult
        fields = ('SessionId', 'UserId')


class LoginSerializer(serializers.ModelSerializer):
    Result = ResultSerializer()

    class Meta:
        model = ETNALogin
        fields = ('ResponseCode', 'Ticket', 'Result')

    def create(self, validated_data):
        result_data = validated_data.pop('Result')
        result = LoginResult.objects.create(**result_data)
        login = ETNALogin.objects.create(Result=result, **validated_data)
        return login


class AccountIdSerializer(serializers.ModelSerializer):
    Result = serializers.ListField(child=serializers.IntegerField())

    class Meta:
        model = AccountId
        fields = ('Result', 'ResponseCode')


class SecurityETNASerializer(serializers.ModelSerializer):
    class Meta:
        model = Security
        fields = ('Description', 'Currency', 'Symbol', 'symbol_id', 'Price')


class OrderETNASerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        exclude = ('id',)
