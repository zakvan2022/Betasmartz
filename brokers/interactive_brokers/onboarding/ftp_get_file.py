'''
This is a file I am using for inbound leg until we
get the inbound leg designed and implemented.
'''

from django.conf import settings
from ftplib import FTP
import os
file = 'Krane_2017-04-21_111608.xml.report.asc'
ftp = FTP(settings.IB_FTP_DOMAIN)
ftp.login(settings.IB_FTP_USERNAME, settings.IB_FTP_PASSWORD)
ftp.cwd('applications/outgoing')
ftp.retrlines('LIST')
ftp.retrbinary('RETR '+ file, open(file, 'wb').write)
ftp.quit()
