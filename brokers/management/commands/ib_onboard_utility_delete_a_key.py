from django.core.management.base import NoArgsCommand
import pdb

class Command(NoArgsCommand):
    def handle_noargs(self, **options):
        '''
        deletes given key from keyring
        '''

        from brokers.interactive_brokers.onboarding import encryption as encr
        from brokers.interactive_brokers.onboarding import onboarding as onboard
        import gnupg

        gpg = gnupg.GPG(gnupghome=onboard.PATH_TO_FILES + onboard.KEYS[:-1], verbose=True)

        key = {'algo': '17',
               'expires': '',
               'keyid': 'CF947C351F46ADA0',
               'ownertrust': '-',
               'sig': '',
               'uids': ['CI Interactive Brokers <ci@interactivebrokers.com>'],
               'fingerprint': '697E25D668048E3B431658CDCF947C351F46ADA0',
               'date': '1261065774',
               'sigs': [],
               'type': 'pub',
               'length': '1024',
               'subkeys': [['6AF986B928167346', 'e', '06EF68B0FC1F6A633CCE1FFA6AF986B928167346']],
               'trust': '-',
               'dummy': ''}

        private = False # 'True' to delete private keys, 'False' for public keys
        
        keys = encr.list_keys(gpg, private)

        print('BEFORE ---------------------------------------')
        print(str(keys))
        keys_before=len(keys)
        print('# of keys:' + str(keys_before))
        print('----------------------------------------------')
        
        encr.delete_key(gpg, key, private)
            
        keys = encr.list_keys(gpg, private)

        print('AFTER ---------------------------------------')
        print(str(keys))
        keys_after=len(keys)
        print('# of keys:' + str(keys_after))
        print(str(keys_before - keys_after) + ' keys deleted')
        print('----------------------------------------------')
        

       

        

        
        
