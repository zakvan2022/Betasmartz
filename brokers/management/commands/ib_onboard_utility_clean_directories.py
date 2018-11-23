from django.core.management.base import NoArgsCommand
from main import constants
from main import abstract
import pandas as pd
import os

class Command(NoArgsCommand):
    def handle_noargs(self, **options):
        '''
        recursively deletes uncompressed, zipped and encrypted directories
        used during creatiion of a file for IB onboarding
        '''

        from brokers.interactive_brokers.onboarding import onboarding as onboard
        from brokers.interactive_brokers.onboarding import onboarding_helpers as onb_help

        import shutil

        dirs = [onb_help.get_onboarding_path_to_files() + onboard.UNCOMPRESSED,
                onb_help.get_onboarding_path_to_files() + onboard.ZIPPED,
                onb_help.get_onboarding_path_to_files() + onboard.ENCRYPTED]

        for d in dirs:
            if os.path.exists(d):
                shutil.rmtree(d)
