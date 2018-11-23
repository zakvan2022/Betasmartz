from django.core.management.base import NoArgsCommand
from main import constants
from main import abstract
import pandas as pd
import os
from django.conf import settings

class Command(NoArgsCommand):
    def handle_noargs(self, **options):
        '''
        deletes all files in the FTP_DIR_INBOUND directory at the IB_FTP site.

        '''

        from brokers.interactive_brokers.onboarding import onboarding as onboard
        from ftplib import FTP

        ftp = FTP(settings.IB_FTP_DOMAIN)
        ftp.login(user=settings.IB_FTP_USERNAME, passwd=settings.IB_FTP_PASSWORD)
        ftp.cwd(onboard.FTP_DIR_INBOUND)

        data_before = []
        ftp.dir(data_before.append)

        files=[]

        file_tail = '.xml.report.asc'
        for i in range(len(data_before)):
            files = files + [elem for elem in data_before[i].split(' ') if len(elem) > len(file_tail) and elem[-len(file_tail):] == file_tail]
        print('files before delete:', files)

        for f in files:
            print('deleting:', f)
            ftp.delete(f)

        data_after = []
        ftp.dir(data_after.append)

        files=[]
        for i in range(len(data_after)):
            files = files + [elem for elem in data_after[i].split(' ') if len(elem) > len(file_tail) and elem[-len(file_tail):] == file_tail]
        print('files after delete:', files)
