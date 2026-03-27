import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
import pandas as pd

django.setup()

from rest_framework.test import APIRequestFactory

from django.db.models import Count

from stocks.models import Sector, StockUniverse
from stocks.views import SectorListView


def main():
    usa_path = r'C:\Users\SHREE\Downloads\USA Top 200 Stocks.xlsx'
    if os.path.exists(usa_path):
        frame = pd.read_excel(usa_path)
        print('USA_COLUMNS', list(frame.columns))
        print('USA_FIRST', frame.head(3).to_dict(orient='records'))

    print('COUNTS', {'sectors': Sector.objects.count(), 'stocks': StockUniverse.objects.filter(is_active=True).count()})
    print(
        'CLASSIFICATION_COUNTS',
        list(
            StockUniverse.objects.values('classification_source')
            .annotate(total=Count('id'))
            .order_by('classification_source')
        ),
    )
    print(
        'USA_SAMPLE',
        list(
            StockUniverse.objects.filter(market='USA')
            .values('symbol', 'company_name', 'sector__name', 'classification_source', 'classification_confidence')[:10]
        ),
    )
    factory = APIRequestFactory()
    for path in ['/api/sectors/', '/api/sectors/?market=INDIA', '/api/sectors/?market=USA']:
        request = factory.get(path)
        response = SectorListView.as_view()(request)
        print('PATH', path)
        print('STATUS', response.status_code)
        print('DATA', response.data[:5] if isinstance(response.data, list) else response.data)


if __name__ == '__main__':
    main()
