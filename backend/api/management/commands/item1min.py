from django.core.management.base import BaseCommand
from api.models import Item_10s, Item_1min
from collections import defaultdict

class Command(BaseCommand):
    help = 'Aggregates Item_10s data by 1 minute and populates Item_1min table with min/max prices and their times for given symbols.'

    def add_arguments(self, parser):
        parser.add_argument(
            'symbols',
            nargs='*',
            type=str,
            help='List of symbols to process (e.g., BTCUSDT ETHUSDT)'
        )

    def handle(self, *args, **options):
        symbols = options['symbols']
        if not symbols:
            self.stdout.write(self.style.WARNING("No symbols provided. Aborting."))
            return

        self.stdout.write(f"Starting 1-minute aggregation for symbols: {', '.join(symbols)}")

        items_to_process = Item_10s.objects.filter(symbol__in=symbols).order_by('time')
        total_count = items_to_process.count()

        if total_count == 0:
            self.stdout.write(self.style.WARNING("No items found for provided symbols."))
            return

        self.stdout.write(f"Total items to process: {total_count}")

        aggregated_data_dict = defaultdict(lambda: {
            'min': float('inf'),
            'max': float('-inf'),
            'min_time': None,
            'max_time': None,
        })

        count = 0
        for item in items_to_process.iterator(chunk_size=10000):
            time_1min = item.time.replace(second=0, microsecond=0)
            key = (time_1min, item.symbol)
            agg = aggregated_data_dict[key]

            if item.min < agg['min']:
                agg['min'] = item.min
                agg['min_time'] = getattr(item, 'min_time', item.time)

            if item.max > agg['max']:
                agg['max'] = item.max
                agg['max_time'] = getattr(item, 'max_time', item.time)

            count += 1
            if count % 10000 == 0:
                self.stdout.write(f"Processed {count} items...")

        self.stdout.write("Aggregation in memory complete. Preparing data for database operations...")

        aggregated_instances = [
            Item_1min(
                time=key[0],
                symbol=key[1],
                min=value['min'],
                max=value['max'],
                min_time=value['min_time'],
                max_time=value['max_time'],
            )
            for key, value in aggregated_data_dict.items()
        ]
        Item_1min.objects.bulk_create(aggregated_instances)

        self.stdout.write(self.style.SUCCESS(f"Done. Processed {count} items total for symbols: {', '.join(symbols)}"))
