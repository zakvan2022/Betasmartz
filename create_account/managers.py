from __future__ import unicode_literals

from io import BytesIO

from django.db import models
from rest_framework.parsers import JSONParser
from rest_framework.renderers import JSONRenderer

from client.models import ClientAccount
from create_account.models import ServiceProfile, InvestmentProfile, \
    SuitabilityProfile, TradeAuthorization, PrincipalApprover, \
    PoliticalExposureDetail, Applicants, Employment, Name, Identity, \
    HomeAddress, Contact, PhoneNumbers, ApplicantSignature, JsonData, \
    FormSchemaHash, FormId, ApexAccount, Forms
from create_account.tasks import request_open_account, request_account_update


class ApexAccountManager(models.Manager):
    @staticmethod
    def create_apex_account(client_account_id):
        # create json
        json_string, apex_account = ApexAccountManager._serialize_apex_account_to_json(client_account_id)

        # send json and receive response - request id
        message = request_open_account.delay(json=json_string).get()
        data = ApexAccountManager._parse(message)
        from create_account.serializers import ApexAccountDeserializer
        serializer = ApexAccountDeserializer(data=data)
        if not serializer.is_valid():
            Exception('received unknown response')

        apex_account.account_id = data['id']
        # would be much nicer from serializer.data['id']
        # - but not sure how to deserialize id - which is not int
        apex_account.request_id = serializer.data['request_id']
        apex_account.save()

        message = request_account_update.delay(request_id=apex_account.request_id).get()
        data = ApexAccountManager._parse(message)
        serializer = ApexAccountDeserializer(data=data)
        if not serializer.is_valid():
            Exception('received unknown response')

        apex_account.status = serializer.data['status']
        apex_account.save()

        return apex_account

    @staticmethod
    def _parse(json_string):
        bytes_string = bytes(json_string, encoding='utf-8')
        stream = BytesIO(bytes_string)
        data = JSONParser().parse(stream)
        return data

    @staticmethod
    def _serialize_apex_account_to_json(client_account_id):
        client_account = ClientAccount.objects.get(id=client_account_id)
        apex_account, objects_to_destroy = ApexAccountManager._create_apex_account_structure(client_account)

        from create_account.serializers import ApexAccountSerializer
        serializer = ApexAccountSerializer(apex_account)
        json_string = JSONRenderer().render(serializer.data)

        for item in objects_to_destroy:
            item.delete()

        return json_string, apex_account

    @staticmethod
    def _create_apex_account_structure(client_account):
        service_profile = ServiceProfile.objects.create()
        investment_profile = InvestmentProfile.objects.create(liquid_net_worth=100002, total_net_worth=100002)
        suitability_profile = SuitabilityProfile.objects.create()
        trade_authorization = TradeAuthorization.objects.create()
        principal_approver = PrincipalApprover.objects.create()
        political_exposure_detail = PoliticalExposureDetail.objects.create(immediate_family= ['Bill Clinton', 'George Bush'],
                                                                           political_organization='ETA')
        applicants = Applicants.objects.create(disclosures=political_exposure_detail,
                                               firm_name='ESET',
                                               company_symbols=['ESET', 'AAPL', 'MSFT'])
        employment = Employment.objects.create(years_employed=1)
        name = Name.objects.create()
        identity = Identity.objects.create(name=name)
        home_address = HomeAddress.objects.create(city='New York',state='New York')
        contact = Contact.objects.create(home_address=home_address)
        phone_numbers = PhoneNumbers.objects.create(contact=contact)
        applicant_signature = ApplicantSignature.objects.create()
        json_data = JsonData.objects.create(applicant_signature=applicant_signature,
                                            registered_rep_approver=principal_approver,
                                            service_profile=service_profile,
                                            investment_profile=investment_profile,
                                            suitability_profile=suitability_profile,
                                            trade_authorization=trade_authorization,
                                            principal_approver=principal_approver,
                                            applicants=applicants,
                                            employment=employment,
                                            identity=identity,
                                            contact=contact)
        form_schema_hash = FormSchemaHash.objects.create(hash='hash', algorithm='SHA-256')
        form_id = FormId.objects.create()
        apex_account = ApexAccount.objects.create(status=0,
                                                  client_account=client_account)
        forms = Forms.objects.create(form_id=form_id,
                                     form_schema_hash=form_schema_hash,
                                     json_data=json_data,
                                     apex_account=apex_account)

        objects_to_destroy = list()
        objects_to_destroy.extend([service_profile, investment_profile, suitability_profile, trade_authorization,
                                   principal_approver, political_exposure_detail, applicants, employment, name, identity,
                                   home_address, contact, phone_numbers, applicant_signature, json_data,
                                   form_schema_hash, form_id, forms])
        return [apex_account, objects_to_destroy]
