import csv
from django.core.management.base import BaseCommand
from datetime import datetime, timezone

from api.models import *  # replace with your actual app name

class Command(BaseCommand):
    help = 'Import trade data from CSV into Item model using bulk_create'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to the CSV file')
        parser.add_argument('--batch-size', type=int, default=1000, help='Number of items per bulk insert')

    def handle(self, *args, **options):
        csv_path = options['csv_file']
        batch_size = 1000000
        items = []
        created_total = 0

        with open(csv_path, newline='') as csvfile:
            reader = csv.DictReader(csvfile)

            for row in reader:
                try:
                    # Convert microsecond timestamp to Python datetime
                    micro_ts = int(row['timestamp'])
                    dt = datetime.fromtimestamp(micro_ts / 1_000_000, tz=timezone.utc)

                    item = Item(
                        time=dt,
                        symbol=row['symbol'],
                        price=(float(row['price']))
                    )
                    items.append(item)

                    if len(items) >= batch_size:
                        Item.objects.bulk_create(items)
                        created_total += len(items)
                        items.clear()

                except Exception as e:
                    self.stderr.write(f"Skipping row due to error: {e}")
                    continue

        # Create any remaining items
        if items:
            Item.objects.bulk_create(items)
            created_total += len(items)

        self.stdout.write(self.style.SUCCESS(f'Successfully imported {created_total} items using bulk_create.'))
