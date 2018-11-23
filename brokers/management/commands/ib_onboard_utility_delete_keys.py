from django.core.management.base import NoArgsCommand
import pdb

class Command(NoArgsCommand):
    def handle_noargs(self, **options):
        '''
        deletes all keys from given keyring
        '''

        from brokers.interactive_brokers.onboarding import encryption as encr
        from brokers.interactive_brokers.onboarding import onboarding as onboard
        import gnupg

        gpg = gnupg.GPG(gnupghome=onboard.PATH_TO_FILES + onboard.KEYS[:-1], verbose=True)

        private = False # 'True' to delete private keys, 'False' for public keys
        keys = encr.list_keys(gpg, private)

        print('BEFORE ---------------------------------------')
        print(str(keys))
        keys_before=len(keys)
        print('# of keys:' + str(keys_before))
        print('----------------------------------------------')
        
        for key in keys:
            encr.delete_key(gpg, key, private)
            
        keys = encr.list_keys(gpg, private)

        print('AFTER ---------------------------------------')
        print(str(keys))
        keys_after=len(keys)
        print('# of keys:' + str(keys_after))
        print(str(keys_before - keys_after) + ' keys deleted')
        print('----------------------------------------------')
        

       

        

        
        
