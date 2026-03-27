from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('analysis', '0002_chatbot_foundation'),
    ]

    operations = [
        migrations.AddField(
            model_name='chatinteractionlog',
            name='feedback_note',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='chatinteractionlog',
            name='feedback_status',
            field=models.CharField(
                choices=[('unrated', 'Unrated'), ('positive', 'Positive'), ('negative', 'Negative')],
                default='unrated',
                max_length=12,
            ),
        ),
    ]
