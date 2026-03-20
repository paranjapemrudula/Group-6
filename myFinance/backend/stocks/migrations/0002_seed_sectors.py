from django.db import migrations


def seed_sectors(apps, schema_editor):
    Sector = apps.get_model('stocks', 'Sector')
    for name in ['Technology', 'Finance', 'Healthcare', 'Energy']:
        Sector.objects.get_or_create(name=name)


def unseed_sectors(apps, schema_editor):
    Sector = apps.get_model('stocks', 'Sector')
    Sector.objects.filter(name__in=['Technology', 'Finance', 'Healthcare', 'Energy']).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('stocks', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_sectors, unseed_sectors),
    ]
