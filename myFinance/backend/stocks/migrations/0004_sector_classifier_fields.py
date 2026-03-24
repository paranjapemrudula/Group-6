from django.db import migrations, models
import django.db.models.deletion


def seed_aliases_and_descriptions(apps, schema_editor):
    Sector = apps.get_model('stocks', 'Sector')
    SectorAlias = apps.get_model('stocks', 'SectorAlias')

    sector_descriptions = {
        'Technology': 'Software, IT services, cloud platforms, semiconductors, hardware, AI, and digital infrastructure companies.',
        'Finance': 'Banks, insurance, asset managers, lending companies, payment networks, exchanges, and financial platforms.',
        'Healthcare': 'Pharmaceuticals, biotechnology, hospitals, medical devices, diagnostics, and healthcare services.',
        'Energy': 'Oil, gas, power, renewables, utilities generation, and energy infrastructure.',
        'Automobile': 'Vehicle manufacturers, auto components, electric vehicles, and mobility platforms.',
        'FMCG': 'Fast-moving consumer goods such as packaged foods, household products, personal care, and beverages.',
        'Consumer Services': 'Retail, travel, hospitality, entertainment, and other direct consumer-facing services.',
        'Consumer Durables': 'Appliances, electronics, home goods, and durable consumer products.',
        'Industrials': 'Capital goods, manufacturing, engineering, logistics, machinery, and industrial services.',
        'Materials': 'Metals, mining, chemicals, cement, construction materials, and raw-material businesses.',
        'Telecom': 'Telecommunications carriers, wireless infrastructure, and network services.',
        'Real Estate': 'Property developers, REITs, construction-linked real estate, and housing businesses.',
        'Services': 'General business services that do not fit more specific sector groups.',
        'Chemicals': 'Specialty chemicals, industrial chemicals, and chemical manufacturing businesses.',
        'Construction': 'Construction, infrastructure development, EPC, and related project businesses.',
        'Uncategorized': 'Fallback sector for rows where source data does not contain enough reliable industry detail yet.',
    }

    aliases = {
        'Technology': ['IT', 'Information Technology', 'Tech'],
        'Finance': ['Financial Services', 'Banking', 'Financials'],
        'Healthcare': ['Health Care', 'Pharma', 'Pharmaceuticals'],
        'Energy': ['Oil Gas & Consumable Fuels', 'Power', 'Oil & Gas'],
        'Automobile': ['Automobile and Auto Components', 'Auto'],
        'FMCG': ['Fast Moving Consumer Goods', 'Consumer Staples'],
        'Industrials': ['Capital Goods', 'Industrial Goods'],
        'Materials': ['Construction Materials', 'Metals & Mining', 'Basic Materials'],
        'Telecom': ['Telecommunication', 'Communication Services'],
        'Real Estate': ['Realty'],
        'Consumer Services': ['Consumer Discretionary', 'Consumer Service'],
        'Consumer Durables': ['Durables'],
    }

    for sector_name, description in sector_descriptions.items():
        sector, _ = Sector.objects.get_or_create(name=sector_name)
        if not sector.description:
            sector.description = description
            sector.save(update_fields=['description'])

    for sector_name, alias_values in aliases.items():
        sector = Sector.objects.filter(name=sector_name).first()
        if not sector:
            continue
        for alias_name in alias_values:
            SectorAlias.objects.get_or_create(
                alias_name=alias_name,
                defaults={'sector': sector},
            )


class Migration(migrations.Migration):

    dependencies = [
        ('stocks', '0003_stockuniverse'),
    ]

    operations = [
        migrations.AddField(
            model_name='sector',
            name='description',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='stockuniverse',
            name='classification_confidence',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=5),
        ),
        migrations.AddField(
            model_name='stockuniverse',
            name='classification_source',
            field=models.CharField(
                choices=[
                    ('RULE', 'Rule Based'),
                    ('ALIAS', 'Alias Match'),
                    ('VECTOR', 'Vector Match'),
                    ('MANUAL', 'Manual'),
                    ('UNKNOWN', 'Unknown'),
                ],
                default='UNKNOWN',
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name='stockuniverse',
            name='raw_sector_label',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.CreateModel(
            name='SectorAlias',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('alias_name', models.CharField(max_length=120, unique=True)),
                ('sector', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='aliases', to='stocks.sector')),
            ],
            options={'ordering': ['alias_name']},
        ),
        migrations.CreateModel(
            name='SectorClassificationLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('stock_symbol', models.CharField(max_length=32)),
                ('company_name', models.CharField(blank=True, max_length=255)),
                ('market', models.CharField(blank=True, max_length=16)),
                ('raw_label', models.CharField(blank=True, max_length=255)),
                (
                    'classification_source',
                    models.CharField(
                        choices=[
                            ('RULE', 'Rule Based'),
                            ('ALIAS', 'Alias Match'),
                            ('VECTOR', 'Vector Match'),
                            ('MANUAL', 'Manual'),
                            ('UNKNOWN', 'Unknown'),
                        ],
                        max_length=16,
                    ),
                ),
                ('confidence', models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                (
                    'predicted_sector',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='classification_logs',
                        to='stocks.sector',
                    ),
                ),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.RunPython(seed_aliases_and_descriptions, migrations.RunPython.noop),
    ]
