from django.core.management.base import BaseCommand
from api.models import *
from collections import defaultdict

class Command(BaseCommand):
    help = 'Aggregates Item_1ms data by 10 milliseconds and populates Item_10ms table with min and max prices.'

    def handle(self, *args, **options):
        self.stdout.write("Starting 10-millisecond aggregation...")

        # Step 1: Fetch all Item_1ms records and aggregate data in memory
        items_to_process = Item_100ms.objects.all().order_by('time')
        total_count = items_to_process.count()
        self.stdout.write(f"Total items to process: {total_count}")

        # Define the time truncation factor (10 milliseconds = 10,000 microseconds)
        n = 1000000

        # Dictionary to store aggregated data: key=(time_10ms, symbol), value={'min': min_price, 'max': max_price}
        aggregated_data_dict = defaultdict(lambda: {'min': float('inf'), 'max': float('-inf')})

        count = 0
        for item in items_to_process.iterator(chunk_size=10000):  # Process in chunks to manage memory
            # Truncate microseconds to the nearest 10 milliseconds
            time_10ms = item.time.replace(microsecond=(item.time.microsecond // n) * n)
            key = (time_10ms, item.symbol)
            aggregated_data_dict[key]['min'] = min(aggregated_data_dict[key]['min'], item.min)
            aggregated_data_dict[key]['max'] = max(aggregated_data_dict[key]['max'], item.max)

            count += 1
            if count % 10000 == 0:
                self.stdout.write(f"Processed {count} items...")

        self.stdout.write("Aggregation in memory complete. Preparing data for database operations...")

        # Convert aggregated data dictionary to list of model instances
        aggregated_instances = [
            Item_1s(
                time=key[0],
                symbol=key[1],
                min=value['min'],
                max=value['max']
            )
            for key, value in aggregated_data_dict.items()
        ]
        Item_1s.objects.bulk_create(aggregated_instances)





        self.stdout.write(self.style.SUCCESS(f"Done. Processed {count} items total."))
