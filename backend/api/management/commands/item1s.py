from django.core.management.base import BaseCommand
from api.models import Item_100ms, Item_1s
from collections import defaultdict

class Command(BaseCommand):
    help = 'Aggregates Item_100ms data by 1 second and populates Item_1s table with min/max prices and their corresponding times for given symbols.'

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

        self.stdout.write(f"Starting 1-second aggregation for symbols: {', '.join(symbols)}")

        items_to_process = Item_100ms.objects.filter(symbol__in=symbols).order_by('time')
        total_count = items_to_process.count()

        if total_count == 0:
            self.stdout.write(self.style.WARNING("No items found for provided symbols."))
            return

        self.stdout.write(f"Total items to process: {total_count}")

        n = 1000000  # 1 second in microseconds

        aggregated_data_dict = defaultdict(lambda: {
            'min': float('inf'),
            'max': float('-inf'),
            'min_time': None,
            'max_time': None,
        })

        count = 0
        for item in items_to_process.iterator(chunk_size=10000):
            time_1s = item.time.replace(microsecond=(item.time.microsecond // n) * n)
            key = (time_1s, item.symbol)
            agg = aggregated_data_dict[key]

            if item.min < agg['min']:
                agg['min'] = item.min
                agg['min_time'] = item.min_time if hasattr(item, 'min_time') else item.time

            if item.max > agg['max']:
                agg['max'] = item.max
                agg['max_time'] = item.max_time if hasattr(item, 'max_time') else item.time

            count += 1
            if count % 10000 == 0:
                self.stdout.write(f"Processed {count} items...")

        self.stdout.write("Aggregation in memory complete. Preparing data for database operations...")

        aggregated_instances = [
            Item_1s(
                time=key[0],
                symbol=key[1],
                min=value['min'],
                max=value['max'],
                min_time=value['min_time'],
                max_time=value['max_time'],
            )
            for key, value in aggregated_data_dict.items()
        ]
        Item_1s.objects.bulk_create(aggregated_instances)

        self.stdout.write(self.style.SUCCESS(f"Done. Processed {count} items total for symbols: {', '.join(symbols)}"))
