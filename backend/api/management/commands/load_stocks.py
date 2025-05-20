import random
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from datetime import timezone as dt_timezone

from api.models import Item


class Command(BaseCommand):
    help = "Populate Item table with stock data for a fixed symbol at equal time intervals"

    def handle(self, *args, **options):
        # Define inputs here directly
        num_rows = 100000000
        start_str = "2005-05-17 09:00:00"
        symbol = ["RA","RB","RC","RD","RE","RF","RG","RH"]
        n=len(symbol)

        naive_start = datetime.strptime(start_str, "%Y-%m-%d %H:%M:%S")
        start_time = timezone.make_aware(naive_start, timezone=dt_timezone.utc)

        self.stdout.write(
            f"Populating {num_rows} rows for symbol '{symbol}' starting from {start_time}"
        )

        interval_seconds = 1

        items_to_create = []
        batch_size = 1000000  # large batch size, adjust if needed
        count=0

        for i in range(num_rows):
            current_time = start_time + timedelta(seconds=i * interval_seconds)

            price = round(random.uniform(10000000, 500000000), 2)
            volume = random.randint(10000, 1000000)
            for s in symbol:
                item = Item(
                    symbol=s,
                    time=current_time,
                    price=price,
                    volume=volume,
                )
                items_to_create.append(item)

            if len(items_to_create) >= batch_size:
                with transaction.atomic():
                    Item.objects.bulk_create(items_to_create)
                print(f"Inserted batch: {count}")
                count+=1
                items_to_create = []

        # Insert remaining items
        if items_to_create:
            with transaction.atomic():
                Item.objects.bulk_create(items_to_create)
            print("Inserted final batch")

        self.stdout.write(self.style.SUCCESS(f"Successfully populated {num_rows} rows"))

# Generate the script to populate the database having CSV rows Timestamp(in milliseconds),Symbol,C1,C2,C3,C4,C5,C6(floats)
