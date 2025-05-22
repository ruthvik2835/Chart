from django.core.management.base import BaseCommand
from django.db.models import Min, Max
from api.models import Item, Item_1ms # Assuming this is your serializer for Item_1ms
from collections import defaultdict

class Command(BaseCommand):
    help = 'Aggregates Item data by millisecond and populates Item_1ms table with min and max prices using serializer and bulk create.'

    def handle(self, *args, **options):
        self.stdout.write("Starting millisecond aggregation...")

        # Step 1: Fetch all items and aggregate data in memory
        items_to_process = Item.objects.all().order_by('time')
        total_count = items_to_process.count()
        self.stdout.write(f"Total items to process: {total_count}")

        # Dictionary to store aggregated data: key=(time_millisecond, symbol), value=(min_price, max_price)
        aggregated_data_dict = defaultdict(lambda: {'min': float('inf'), 'max': float('-inf')})

        count = 0
        for item in items_to_process.iterator(chunk_size=10000):  # Process in chunks to manage memory
            # Truncate microseconds to milliseconds
            time_millisecond = item.time.replace(microsecond=(item.time.microsecond // 1000) * 1000)
            key = (time_millisecond, item.symbol)
            aggregated_data_dict[key]['min'] = min(aggregated_data_dict[key]['min'], item.price)
            aggregated_data_dict[key]['max'] = max(aggregated_data_dict[key]['max'], item.price)

            count += 1
            if count % 10000 == 0:
                self.stdout.write(f"Processed {count} items...")

        self.stdout.write("Aggregation in memory complete. Preparing data for serializer...")

        # Convert aggregated data dictionary to list of dictionaries for serializer
        aggregated_instances = [
            Item_1ms(
                time=key[0],
                symbol=key[1],
                min=value['min'],
                max=value['max']
            )
            for key, value in aggregated_data_dict.items()
        ]

        Item_1ms.objects.bulk_create(aggregated_instances)


        self.stdout.write(self.style.SUCCESS(f"Done. Processed {count} items total."))
