# your_app/management/commands/load_items_from_csv.py

import csv
from django.core.management.base import BaseCommand
from django.db import transaction

import random

from api.models import Item  # Use model directly for speed


class Command(BaseCommand):
    help = 'Load items from a CSV file and populate the Item model'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to the CSV file')

    def handle(self, *args, **options):
        csv_path = options['csv_file']
        batch_size = 10000000
        items_to_create = []

        try:
            # with open(csv_path, newline='', encoding='utf-8') as csvfile:
            #     reader = csv.DictReader(csvfile)

                for i in range(1,10000):
                    name, value = random.randint(0,10000),random.randint(0,10000)
                    items_to_create.append(Item(name=name, value=value))
                    if len(items_to_create) >= batch_size:
                        with transaction.atomic():
                            Item.objects.bulk_create(items_to_create, batch_size=batch_size)
                        items_to_create.clear()
                        self.stdout.write(self.style.SUCCESS(f"Inserted batch {i // batch_size}"))

                if items_to_create:
                    with transaction.atomic():
                        Item.objects.bulk_create(items_to_create, batch_size=batch_size)

                self.stdout.write(self.style.SUCCESS("✔️ Finished loading all items."))

        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f"❌ File not found: {csv_path}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ An error occurred: {str(e)}"))
