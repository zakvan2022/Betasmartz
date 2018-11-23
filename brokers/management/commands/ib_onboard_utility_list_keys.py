from django.core.management.base import NoArgsCommand

class Command(NoArgsCommand):
    def handle_noargs(self, **options):
        '''
        lists all private keys on private keyring and all public keys on
        public keyring
        '''

        from brokers.interactive_brokers.onboarding import encryption as encr
        from brokers.interactive_brokers.onboarding import onboarding as onboard
        from brokers.interactive_brokers.onboarding import onboarding_helpers as onb_help
        import gnupg

        gpg = gnupg.GPG(gnupghome=onb_help.get_onboarding_path_to_files() + onboard.KEYS[:-1], verbose=True)
        
        private_keys = encr.list_keys(gpg, True)
        public_keys = encr.list_keys(gpg, False)

        print('PRIVATE---------------------------------------')
        print(str(private_keys))
        print('# of PRIVATE keys:' + str(len(private_keys)))
        print('PUBLIC---------------------------------------')
        print(str(public_keys))
        print('# of PUBLIC keys:' + str(len(public_keys)))
        print('---------------------------------------')
       

        

        
        
