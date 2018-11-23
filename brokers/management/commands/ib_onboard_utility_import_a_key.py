from django.core.management.base import NoArgsCommand
import pdb
import io

class Command(NoArgsCommand):
    def handle_noargs(self, **options):
        '''
        imports a public key to public keyring
        '''

        from brokers.interactive_brokers.onboarding import encryption as encr
        from brokers.interactive_brokers.onboarding import onboarding as onboard
        import gnupg

        path_to_files = onboard.PATH_TO_FILES
        keys_dir = onboard.KEYS[:-1]
        ib_public_key = onboard.IB_PUBLIC_KEY
    
        gpg = gnupg.GPG(gnupghome=path_to_files + keys_dir, verbose=True)

        public_keys = encr.list_keys(gpg, False)

        print('Public Keys BEFORE ---------------------------------------')
        print(str(public_keys))
        keys_before=len(public_keys)
        print('# of public keys:' + str(keys_before))
        print('----------------------------------------------')

        with io.open(path_to_files + keys_dir + ib_public_key, 'r') as pub_key_file_stream:
            pub_key_data = pub_key_file_stream.read()

        gpg.import_keys(pub_key_data) 
        public_keys = encr.list_keys(gpg, False)

        print('Public Keys AFTER ---------------------------------------')
        print(str(public_keys))
        keys_after=len(public_keys)
        print('# of public keys:' + str(keys_after))
        print(str(keys_after - keys_before) + ' keys imported')
        print('----------------------------------------------')
        

       

        

        
        
