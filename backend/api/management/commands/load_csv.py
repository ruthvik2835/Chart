import csv
from datetime import datetime, timezone as dt_timezone

from django.core.management.base import BaseCommand
from django.db import transaction

from api.models import Item
import time


class Command(BaseCommand):
    help = 'Efficiently load items from a large CSV file in batches.'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to the CSV file')
        parser.add_argument('--batch-size', type=int, default=int(1e7), help='Number of rows to insert per batch (default: 1e7)')

    def handle(self, *args, **options):
        csv_file = options['csv_file']
        batch_size = options['batch_size']
        start_time = time.time()

        def parse_csv():
            with open(csv_file, 'r', newline='') as f:
                reader = csv.reader(f)
                header = next(reader)

                expected_columns = ['Timestamp', 'Symbol', 'C1', 'C2', 'C3', 'C4', 'C5', 'C6']
                if header != expected_columns:
                    raise ValueError(f"CSV header mismatch. Expected: {expected_columns}")

                for row_num, row in enumerate(reader, start=2):
                    try:
                        timestamp = datetime.fromisoformat(row[0].replace('Z', '+00:00'))

                        yield Item(
                            time=timestamp,
                            symbol=row[1],
                            c1=float(row[2]),
                            c2=float(row[3]),
                            c3=float(row[4]),
                            c4=float(row[5]),
                            c5=float(row[6]),
                            c6=float(row[7]),
                        )
                    except Exception as e:
                        self.stderr.write(f"Skipping row {row_num} due to error: {e}")

        total_inserted = 0
        batch = []

        for item in parse_csv():
            batch.append(item)
            if len(batch) >= batch_size:
                with transaction.atomic():
                    Item.objects.bulk_create(batch, batch_size=batch_size)
                total_inserted += len(batch)
                elapsed = time.time() - start_time
                self.stdout.write(f"Inserted {total_inserted} items... Time taken: {elapsed / 60:.2f} minutes")
                batch.clear()

        # Insert any remaining items
        if batch:
            with transaction.atomic():
                Item.objects.bulk_create(batch, batch_size=batch_size)
            total_inserted += len(batch)

        elapsed = time.time() - start_time
        self.stdout.write(self.style.SUCCESS(f"Finished. Total inserted: {total_inserted} items."))
        self.stdout.write(self.style.SUCCESS(f"Time taken: {elapsed / 60:.2f} minutes"))

