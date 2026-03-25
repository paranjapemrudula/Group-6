from django.core.management.base import BaseCommand, CommandError

from stocks.services import import_stock_universe


class Command(BaseCommand):
    help = 'Import India and USA stock universe files into the database.'

    def add_arguments(self, parser):
        parser.add_argument('--india', dest='india_path')
        parser.add_argument('--usa', dest='usa_path')
        parser.add_argument('--deactivate-missing', action='store_true')

    def handle(self, *args, **options):
        india_path = options.get('india_path')
        usa_path = options.get('usa_path')

        if not india_path and not usa_path:
            raise CommandError('Provide at least one file path with --india or --usa.')

        imported = import_stock_universe(
            india_path=india_path,
            usa_path=usa_path,
            deactivate_missing=options.get('deactivate_missing', False),
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Imported INDIA={imported['INDIA']} USA={imported['USA']} rows into StockUniverse."
            )
        )
