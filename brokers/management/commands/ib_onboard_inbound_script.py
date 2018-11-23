# Stdlib imports
import os
import gnupg
import io
from ftplib import FTP
import xml.etree.ElementTree as ET

# Core Django imports
from django.core.management.base import NoArgsCommand
from django.conf import settings

# App imports
from ...interactive_brokers.onboarding import onboarding as onboard
from ...interactive_brokers.onboarding import onboarding_helpers as onb_help
from client.models import Client, IBOnboard

class Command(NoArgsCommand):
    def handle_noargs(self, **options):

        # connect to IB's FTP site
        ftp = FTP(settings.IB_FTP_DOMAIN)
        ftp.login(settings.IB_FTP_USERNAME, settings.IB_FTP_PASSWORD)
        ftp.cwd(onboard.FTP_DIR_INBOUND)

        # get files to fetch
        data_before = []
        ftp.dir(data_before.append)
        files=[]
        file_tail = '.xml.report.asc'
        for i in range(len(data_before)):
            files = files + [elem for elem in data_before[i].split(' ') if len(elem) > len(file_tail) and elem[-len(file_tail):] == file_tail]

        # set up dictionaries to track responses
        response = {}
        entity = {}
        external_id = {}
        status = {}
        user_id = {}
        password = {}
        user = {}
        account = {}

        # decrypt and parse each file
        gpg = gnupg.GPG(gnupghome=onb_help.get_onboarding_path_to_files() + onboard.KEYS[:-1], verbose=False)

        for f in files:
            ftp.retrbinary('RETR '+ f, open(f, 'wb').write)
            with io.open(f, 'rb') as encrypted_file_stream:
                decrypted_data = gpg.decrypt_file(encrypted_file_stream)
                xml_response = str(decrypted_data)
                response[f] = xml_response
                print(xml_response)
                root = ET.fromstring(xml_response)

                # get entity and external_id - NB there may be more than one per response
                ext_id = []
                ent = {} # use dictionary, with external_id as key to match entities with ext_id
                entities = root.find('Applications').find('Application').find('Entities')
                for en in entities:
                    ext_id.append(en.get('external_id'))
                    ent[en.get('external_id')] = en.text
                entity[f] = ent
                external_id[f] = ext_id

                # get the rest
                status[f] = root.find('Applications').find('Application').get('Status')
                user_id[f] = root.find('Applications').find('Application').find('Users').find('User').get('user_id')
                password[f] = root.find('Applications').find('Application').find('Users').find('User').get('password')
                user[f] = root.find('Applications').find('Application').find('Users').find('User').text
                account[f] = root.find('Applications').find('Application').find('Accounts').find('Account').text

        # delete files ftped to local directory
        for f in files:
            os.remove(f)

        # pack data to db
        for f in files:
            for ext_id in external_id[f]:
                try:
                    ib_onboard_client = Client.objects.get(id=ext_id)
                    ib_onboard_db = IBOnboard.objects.get(client=ib_onboard_client)

                    # save copy of inbound xml
                    if not ib_onboard_db.xml_inbound:
                        ib_onboard_db.xml_inbound = {}
                    ib_onboard_db.xml_inbound[f] = response[f]

                    # save the rest if response status is 'Success'
                    if status[f] == 'Success':
                        ib_onboard_db.account_number = account[f]
                        ib_onboard_db.ib_entity = entity[f][ext_id]
                        ib_onboard_db.ib_user_id = user_id[f]
                        ib_onboard_db.ib_password = password[f]
                        ib_onboard_db.ib_user = user[f]
                        ib_onboard_db.state = IBOnboard.STATE_ACTIVE
                    ib_onboard_db.save()

                except:
                    status[f] = 'Failed'
                    print('Client with external_id=%s not found'%ext_id)

        # delete successful inbound files
        for f in files:
            if status[f] == 'Success':
                print('deleting:', f)
                ftp.delete(f)
        ftp.quit()


