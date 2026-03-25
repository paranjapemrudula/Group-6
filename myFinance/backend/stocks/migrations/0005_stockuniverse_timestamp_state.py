from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('stocks', '0004_sync_stockuniverse_schema'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AddField(
                    model_name='stockuniverse',
                    name='created_at',
                    field=models.DateTimeField(auto_now_add=True, default=None),
                    preserve_default=False,
                ),
                migrations.AddField(
                    model_name='stockuniverse',
                    name='updated_at',
                    field=models.DateTimeField(auto_now=True, default=None),
                    preserve_default=False,
                ),
            ],
        ),
    ]
