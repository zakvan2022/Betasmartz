import csv

from .models import Client
from address.models import Address
from advisor.models import Advisor
from user.models import User

CLIENT_IMPORT_FIELDS = [
    # 'salutation',
    # 'suffix',
    'gender',
    'phone_num',
    'civil_status',
    'date_of_birth',
    'politically_exposed',
    'employment_status',
    'employer',
]

CLIENT_USER_IMPORT_FIELDS = [
    'first_name',
    'middle_name',
    'last_name',
    'email',
]

CLIENT_ADDRESS_IMPORT_FIELDS = [
    'address1',
    'address2',
    'city',
    'post_code',
    'state_code',
    'country',
]

ADVISOR_IMPORT_FIELDS = [
    'gender',
]

ADVISOR_USER_IMPORT_FIELDS = [
    'email',
    'first_name',
    'middle_name',
    'last_name',
]

ADVISOR_ADDRESS_IMPORT_FIELDS = [
    'address1',
    'address2',
    'city',
    'post_code',
    'state_code',
    'country',
]

def import_client_from_csv(csvfile, firm):
    decoded_file = csvfile.read().decode('utf-8').splitlines()
    reader = csv.DictReader(decoded_file)
    for row in reader:
        client_user_dict = { key: row[key] for key in CLIENT_USER_IMPORT_FIELDS if row[key] is not None and row[key] is not '' }
        client_address_dict = { key: row[key] for key in CLIENT_ADDRESS_IMPORT_FIELDS if row[key] is not None and row[key] is not '' }
        client_dict = { key: row[key] for key in CLIENT_IMPORT_FIELDS if row[key] is not None and row[key] is not '' }

        advisor_user_dict = { key: row['advisor_' + key] for key in ADVISOR_USER_IMPORT_FIELDS if row['advisor_' + key] is not None and row['advisor_' + key] is not '' }
        advisor_address_dict = { key: row['advisor_' + key] for key in ADVISOR_ADDRESS_IMPORT_FIELDS if row['advisor_' + key] is not None and row['advisor_' + key] is not '' }
        advisor_dict = { key: row['advisor_' + key] for key in ADVISOR_IMPORT_FIELDS if row['advisor_' + key] is not None and row['advisor_' + key] is not '' }

        try:
            User.objects \
                .filter(email=advisor_user_dict['email']) \
                .update(**advisor_user_dict)
            advisor_user = User.objects.get(email=advisor_user_dict['email'])
        except Exception as e:
            advisor_user = User.objects.create(**advisor_user_dict)

        advisor_address = Address()
        advisor_address.update_address(**advisor_address_dict)
        advisor_address.save()

        try:
            advisor = Advisor.objects.get(user__email=advisor_user_dict['email'])
            Advisor.objects \
                .filter(user__email=advisor_user_dict['email']) \
                .update(residential_address = advisor_address, **advisor_dict)
        except:
            advisor = Advisor(**advisor_dict)
            advisor.user = advisor_user
            advisor.residential_address = advisor_address

            advisor.firm = firm
            advisor.betasmartz_agreement = True
            advisor.default_portfolio_set = firm.default_portfolio_set
            advisor.is_accepted = True

            advisor.save()

        try:
            User.objects \
                .filter(email=client_user_dict['email']) \
                .update(**client_user_dict)
            client_user = User.objects.get(email=client_user_dict['email'])
        except Exception as e:
            client_user = User.objects.create(**client_user_dict)

        client_address = Address()
        client_address.update_address(**client_address_dict)
        client_address.save()

        try:
            Client.objects \
                .filter(user__email=client_user_dict['email']) \
                .update(residential_address = client_address, advisor=advisor, **client_dict)
            client = Client.objects.get(user__email=client_user_dict['email'])
        except:
            client = Client(**client_dict)
            client.user = client_user
            client.residential_address = client_address
            client.advisor = advisor

            client.betasmartz_agreement = True
            client.default_portfolio_set = firm.default_portfolio_set
            client.is_accepted = True

            client.save()
