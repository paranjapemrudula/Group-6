from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('stocks', '0002_seed_sectors'),
    ]

    operations = [
        migrations.CreateModel(
            name='StockUniverse',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('symbol', models.CharField(max_length=32)),
                ('company_name', models.CharField(max_length=255)),
                ('market', models.CharField(choices=[('INDIA', 'India'), ('USA', 'USA')], max_length=16)),
                ('series', models.CharField(blank=True, max_length=32)),
                ('isin_code', models.CharField(blank=True, max_length=32)),
                ('source_file', models.CharField(blank=True, max_length=255)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('sector', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='universe_stocks', to='stocks.sector')),
            ],
            options={
                'ordering': ['market', 'company_name'],
                'unique_together': {('symbol', 'market')},
            },
        ),
    ]
