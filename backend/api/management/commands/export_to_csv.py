import os
import csv
from datetime import datetime

from django.core.management.base import BaseCommand
from django.apps import apps
from django.conf import settings

# List your model names here (app_label.ModelName)
MODELS = [
    'api.Item',
    'api.Item_1ms',
    'api.Item_10ms',
    'api.Item_100ms',
    'api.Item_1s',
    'api.Item_10s',
    'api.Item_1min',
]

OUTPUT_DIR = os.path.join(settings.BASE_DIR, 'csv_exports')


class Command(BaseCommand):
    help = 'Export specified Django models to CSV, renaming min/max fields'

    def handle(self, *args, **options):
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        self.stdout.write(f"Exporting to directory: {OUTPUT_DIR}\n")

        for model_path in MODELS:
            app_label, model_name = model_path.split('.', 1)
            model = apps.get_model(app_label, model_name)
            if model is None:
                self.stderr.write(f"❌ Could not find model {model_path}, skipping.")
                continue

            qs = model.objects.all()
            if not qs.exists():
                self.stdout.write(f"⚠️  {model_name} has no rows, skipping.")
                continue

            # Build header row, renaming min/max where needed
            field_names = [f.name for f in model._meta.fields]
            header = []
            for name in field_names:
                if name == 'min':
                    header.append('min_price')
                elif name == 'max':
                    header.append('max_price')
                else:
                    header.append(name)

            csv_path = os.path.join(OUTPUT_DIR, f"{model_name}.csv")
            with open(csv_path, 'w', newline='', encoding='utf-8') as fp:
                writer = csv.writer(fp)
                writer.writerow(header)

                # Use iterator() to avoid large memory usage
                for obj in qs.iterator():
                    row = []
                    for name in field_names:
                        value = getattr(obj, name)
                        # format datetimes as ISO strings
                        if isinstance(value, datetime):
                            value = value.isoformat()
                        row.append(value)
                    writer.writerow(row)

            self.stdout.write(f"✅ Wrote {qs.count()} rows to {csv_path}")

        self.stdout.write("\nAll done.")
