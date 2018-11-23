import pandas as pd
import numpy as np
from datetime import datetime
from functools import reduce

from django.core.management.base import BaseCommand
from portfolios.models import MarketIndex, Region


def get_unique_index(excel_file_path):
    """
    This function reads an excel file and populates MarketIndex model.
    It assumes that columns in the file are in the following order.
    INDEX, DESCRIPTION, CURRENCY, REGION

    :return: indexes, descriptions, currencies, regions fields
    """

    df = pd.read_excel(excel_file_path)
    df = df[df.columns[0:]]
    df = df.dropna(axis=0, how='all')
    # Extracts the indexes from the sheet
    indexes = df["INDEX"].values
    descriptions = df["DESCRIPTION"].values
    currencies = df["CURRENCY"].values
    regions = df["REGION"].values
    # Extracts the tickers from the sheet
    
    return indexes, descriptions, currencies, regions


class Command(BaseCommand):
    help = 'Populates the market index from excel.'

    def add_arguments(self, parser):
        # Positional arguments
        parser.add_argument('excel_file_path', nargs='+', type=str)

    def handle(self, *args, **options):
        excel_file_path = options['excel_file_path']
        excel_file_path = excel_file_path[0]

        indexes, descriptions, currencies, regions = get_unique_index(excel_file_path)

        array_index = 0
        region_maps = {}
        for region in Region.objects.all().values('name', 'id'):
            region_maps[region['name']] = region['id']

        for index in indexes:
            currency = currencies[array_index]
            description = descriptions[array_index]
            region = regions[array_index]

            filtered_marketIndex = MarketIndex.objects.filter(data_api_param__iexact=index)
            intersect = filtered_marketIndex.count()
            
            if intersect > 0:
                filtered_marketIndex.update(
                    currency=currency,
                    description=description,
                    region_id=region_maps.get(region) or region_maps.get('INT'),
                )
            else:
                new_marketIndex = MarketIndex(
                    display_name=index,
                    data_api_param=index,
                    currency=currency,
                    data_api='portfolios.api.bloomberg',
                    url='https://bloomberg.com',
                    region_id=region_maps.get(region) or region_maps.get('INT'),
                    description=description
                )
                new_marketIndex.save()
            array_index += 1

