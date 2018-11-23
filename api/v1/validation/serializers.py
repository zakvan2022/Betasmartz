from rest_framework import serializers
from phonenumber_field.phonenumber import PhoneNumber
from brokers.models import IBAccountFeed
from client.models import IBOnboard, EmailInvite
from firm.models import FirmEmailInvite
from user.models import User


class PhoneNumberValidationSerializer(serializers.Serializer):
    number = serializers.CharField()

    def validate_number(self, number):
        number = number.strip('\/[]*&^%$#@').replace('-', '').replace(' ', '').replace('(', '').replace(')', '')
        try:
            num = PhoneNumber.from_string(number)
        except Exception as e:
            raise serializers.ValidationError(e)

        if not num.is_valid():
            raise serializers.ValidationError('Invalid phone number')
        return number


class EmailValidationSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, email):
        if User.objects.filter(email=email).count() > 0:
            raise serializers.ValidationError('The email is already in use')
        if EmailInvite.objects.filter(email=email).count() > 0:
            raise serializers.ValidationError('The email is already in use')
        if FirmEmailInvite.objects.filter(email=email).count() > 0:
            raise serializers.ValidationError('The email is already in use')
        return email


class IBAccountValidationSerializer(serializers.Serializer):
    account_number = serializers.CharField()

    def validate_account_number(self, account_number):
        if IBAccountFeed.objects.filter(account_id=account_number).count() == 0:
            raise serializers.ValidationError('IB account number is not available')

        if IBOnboard.objects.filter(account_number=account_number).count() > 0:
            raise serializers.ValidationError('Another client already exists with this IB account number')
        return account_number

class CompositeValidationSerializer(serializers.Serializer):
    phone_numbers = serializers.ListField(required=False)
    emails = serializers.ListField(required=False)
    ib_account_numbers = serializers.ListField(required=False)

    def validate_phone_numbers(self, phone_numbers):
        res_phone_numbers = []
        for phone_number in phone_numbers:
            data = {'number': phone_number}
            serializer = PhoneNumberValidationSerializer(data=data)
            if serializer.is_valid():
                res_phone_numbers.append(data)
            else:
                res_phone_numbers.append({
                    **data,
                    'errors': serializer.errors['number']
                })
        return res_phone_numbers

    def validate_emails(self, emails):
        res_emails = []
        for email in emails:
            data = {'email': email}
            serializer = EmailValidationSerializer(data=data)
            if serializer.is_valid():
                res_emails.append(data)
            else:
                res_emails.append({
                    **data,
                    'errors': serializer.errors['email']
                })
        return res_emails

    def validate_ib_account_numbers(self, ib_account_numbers):
        res_ib_account_numbers = []
        for account_number in ib_account_numbers:
            data = {'account_number': account_number}
            serializer = IBAccountValidationSerializer(data=data)
            if serializer.is_valid():
                res_ib_account_numbers.append(data)
            else:
                res_ib_account_numbers.append({
                    **data,
                    'errors': serializer.errors['account_number']
                })
        return res_ib_account_numbers
