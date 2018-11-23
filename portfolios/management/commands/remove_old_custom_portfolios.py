from django.core.management.base import BaseCommand

from goal.models import Goal


class Command(BaseCommand):
    help = ''

    def handle(self, *args, **options):
        for goal in Goal.objects.all():
            goal.portfolios = None
            goal.save()
