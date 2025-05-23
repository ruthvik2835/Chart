from django.core.management.base import BaseCommand
from api.models import Item_1ms, Item_10ms
from collections import defaultdict

class Command(BaseCommand):
    help = 'Aggregates Item_1ms data by 10 milliseconds and populates Item_10ms table with min/max prices and times for given symbols.'

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

        self.stdout.write(f"Starting 10-millisecond aggregation for symbols: {', '.join(symbols)}")

        items_to_process = Item_1ms.objects.filter(symbol__in=symbols).order_by('time')
        total_count = items_to_process.count()

        if total_count == 0:
            self.stdout.write(self.style.WARNING("No items found for provided symbols."))
            return

        self.stdout.write(f"Total items to process: {total_count}")

        n = 10000  # 10 ms in microseconds

        aggregated_data_dict = defaultdict(lambda: {
            'min_price': float('inf'),
            'max_price': float('-inf'),
            'min_time': None,
            'max_time': None,
        })

        count = 0
        for item in items_to_process.iterator(chunk_size=10000):
            time_10ms = item.time.replace(microsecond=(item.time.microsecond // n) * n)
            key = (time_10ms, item.symbol)
            agg = aggregated_data_dict[key]

            if item.min < agg['min_price']:
                agg['min_price'] = item.min
                agg['min_time'] = item.min_time

            if item.max > agg['max_price']:
                agg['max_price'] = item.max
                agg['max_time'] = item.max_time

            count += 1
            if count % 10000 == 0:
                self.stdout.write(f"Processed {count} items...")

        self.stdout.write("Aggregation in memory complete. Preparing data for database operations...")

        aggregated_instances = [
            Item_10ms(
                time=key[0],
                symbol=key[1],
                min=value['min_price'],
                max=value['max_price'],
                min_time=value['min_time'],
                max_time=value['max_time'],
            )
            for key, value in aggregated_data_dict.items()
        ]

        Item_10ms.objects.bulk_create(aggregated_instances)

        self.stdout.write(self.style.SUCCESS(
            f"Done. Aggregated {len(aggregated_instances)} 10ms-symbol pairs for: {', '.join(symbols)}"
        ))
