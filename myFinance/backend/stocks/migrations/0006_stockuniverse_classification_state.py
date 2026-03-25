from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('stocks', '0005_stockuniverse_timestamp_state'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AddField(
                    model_name='stockuniverse',
                    name='classification_confidence',
                    field=models.DecimalField(decimal_places=2, default=1, max_digits=5),
                    preserve_default=False,
                ),
                migrations.AddField(
                    model_name='stockuniverse',
                    name='classification_source',
                    field=models.CharField(default='import', max_length=50),
                    preserve_default=False,
                ),
            ],
        ),
    ]
