from django.core.management.base import NoArgsCommand
import pdb

class Command(NoArgsCommand):
    def handle_noargs(self, **options):

        from brokers.interactive_brokers.onboarding import encryption as encr
        from brokers.interactive_brokers.onboarding import onboarding as onboard
        import gnupg
        '''
        generates a new public and private key.

        Only run this command if there is no private key already saved to the
        private key ring.

        This check is made below.

        To delete an existing private key, run the command
        './manage.py onboard_utility_delete_keys' having first set private=True  
        '''

        gpg = gnupg.GPG(gnupghome=onboard.PATH_TO_FILES + onboard.KEYS[:-1],
                        verbose=True)

        existing_private_keys = encr.list_keys(gpg, True)
        
        print('PRIVATE---------------------------------------')
        print(str(existing_private_keys))
        print('# of PRIVATE keys:' + str(len(existing_private_keys)))
        print('---------------------------------------')
        
        if len(existing_private_keys) > 0:
            raise Exception('There is already a private key in the private key ring.')
        
        encr.gen_key(onboard.PATH_TO_FILES,
                     onbboard.KEYS[:-1],
                     onboard.BETASMARTZ_PUBLIC_KEY)

       

        

        
        
