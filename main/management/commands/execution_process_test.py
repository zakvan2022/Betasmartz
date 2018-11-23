from django.core.management.base import NoArgsCommand

class Command(NoArgsCommand):
    def handle_noargs(self, **options):
        '''
        runs process(data_provider, execution_provider, delay) in betasmartz / execution / end_of_day.py 
        '''
        from datetime import datetime
        from execution.end_of_day import process
        from portfolios.providers.execution.django import ExecutionProviderDjango
        from portfolios.providers.data.django import DataProviderDjango
        data_provider = DataProviderDjango(datetime.now().date())
        execution_provider = ExecutionProviderDjango()
        process(data_provider, execution_provider, 5)
        

        
