from django.core.management.base import BaseCommand, CommandError

from stocks.models import StockUniverse
from stocks.services import import_stock_universe_file


class Command(BaseCommand):
    help = 'Import stock universe data from India CSV and USA CSV/XLSX files.'

    def add_arguments(self, parser):
        parser.add_argument('--india', type=str, help='Path to India stock universe CSV file.')
        parser.add_argument('--usa', type=str, help='Path to USA stock universe CSV/XLSX file.')
        parser.add_argument(
            '--deactivate-missing',
            action='store_true',
            help='Deactivate imported market rows before refreshing them from the source files.',
        )

    def handle(self, *args, **options):
        india_path = options.get('india')
        usa_path = options.get('usa')
        deactivate_missing = options.get('deactivate_missing')

        if not india_path and not usa_path:
            raise CommandError('Provide at least one source file using --india or --usa.')

        summaries = []
        if india_path:
            if deactivate_missing:
                StockUniverse.objects.filter(market=StockUniverse.MARKET_INDIA).update(is_active=False)
            summaries.append(import_stock_universe_file(file_path=india_path, market=StockUniverse.MARKET_INDIA))

        if usa_path:
            if deactivate_missing:
                StockUniverse.objects.filter(market=StockUniverse.MARKET_USA).update(is_active=False)
            summaries.append(import_stock_universe_file(file_path=usa_path, market=StockUniverse.MARKET_USA))

        for summary in summaries:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Imported {summary['imported_count']} rows for {summary['market']} from {summary['source_file']}"
                )
            )
