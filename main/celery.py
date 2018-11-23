from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from main import settings

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'main.settings')

app = Celery('main',
             broker=settings.REDIS_URI,
             backend=settings.REDIS_URI)

# Optional configuration, see the application user guide.
app.conf.update(
    result_expires=3600,
)

app.autodiscover_tasks()

if __name__ == '__main__':
    app.start()
