# Generated migration for series_code field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("bills", "0004_bill_date_bill_state"),
    ]

    operations = [
        migrations.AddField(
            model_name="bill",
            name="series_code",
            field=models.CharField(
                blank=True,
                help_text="Invoice series code from B2B Router (e.g., 'S' for cuotas, 'F' for servicios).",
                max_length=16,
                null=True,
                verbose_name="series code",
            ),
        ),
    ]
