from django.core.management.base import BaseCommand
from api.models import *
from collections import defaultdict

class Command(BaseCommand):

    def handle(self, *args, **options):
        self.stdout.write("Starting 10-second aggregation...")

        items_to_process = Item_1s.objects.all().order_by('time')
        total_count = items_to_process.count()
        self.stdout.write(f"Total items to process: {total_count}")

        n = 10000000
        aggregated_data_dict = defaultdict(lambda: {'min': float('inf'), 'max': float('-inf')})

        count = 0
        for item in items_to_process.iterator(chunk_size=10000): 
            time_10s = item.time.replace(second=(item.time.second // 10) * 10, microsecond=0)
            key = (time_10s, item.symbol)
            aggregated_data_dict[key]['min'] = min(aggregated_data_dict[key]['min'], item.min)
            aggregated_data_dict[key]['max'] = max(aggregated_data_dict[key]['max'], item.max)

            count += 1
            if count % 100 == 0:
                print(time_10s)
                self.stdout.write(f"Processed {count} items...")

        self.stdout.write("Aggregation in memory complete. Preparing data for database operations...")

        # Convert aggregated data dictionary to list of model instances
        aggregated_instances = [
            Item_10s(
                time=key[0],
                symbol=key[1],
                min=value['min'],
                max=value['max']
            )
            for key, value in aggregated_data_dict.items()
        ]
        Item_10s.objects.bulk_create(aggregated_instances)





        self.stdout.write(self.style.SUCCESS(f"Done. Processed {count} items total."))
