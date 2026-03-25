from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('stocks', '0006_stockuniverse_classification_state'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AddField(
                    model_name='sector',
                    name='description',
                    field=models.TextField(blank=True, default=''),
                    preserve_default=False,
                ),
            ],
        ),
    ]
