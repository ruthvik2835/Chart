from django.core.management.base import BaseCommand
from api.models import *

class Command(BaseCommand):
    help = 'Aggregates Item data by millisecond and populates Item_1ms table with min and max prices.'

    def handle(self, *args, **options):
        self.stdout.write("Starting millisecond aggregation...")

        count = 0

        items_to_process = Item.objects.all().order_by('time')

        for item_micro in items_to_process:
            time_millisecond = item_micro.time.replace(microsecond=(item_micro.time.microsecond // 1000) * 1000)
            millisecond_entry, created = Item_1ms.objects.get_or_create(
                time=time_millisecond,
                symbol=item_micro.symbol,
                defaults={
                    'min': item_micro.price,
                    'max': item_micro.price
                }
            )

            if not created:
                updated = False
                if item_micro.price < millisecond_entry.min:
                    millisecond_entry.min = item_micro.price
                    updated = True
                if item_micro.price > millisecond_entry.max:
                    millisecond_entry.max = item_micro.price
                    updated = True

                if updated:
                    millisecond_entry.save(update_fields=['min', 'max'])

            count += 1
            if count % 1000 == 0:
                self.stdout.write(f"Processed {count} items...")

        self.stdout.write(self.style.SUCCESS(f"Done. Processed {count} items total."))
