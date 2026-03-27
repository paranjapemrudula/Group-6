from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('portfolios', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserPreference',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('risk_level', models.CharField(choices=[('conservative', 'Conservative'), ('balanced', 'Balanced'), ('aggressive', 'Aggressive')], default='balanced', max_length=20)),
                ('investment_horizon', models.CharField(choices=[('short', 'Short Term'), ('medium', 'Medium Term'), ('long', 'Long Term')], default='medium', max_length=20)),
                ('preferred_sectors', models.JSONField(blank=True, default=list)),
                ('avoid_sectors', models.JSONField(blank=True, default=list)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='recommendation_preference', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['user__username']},
        ),
        migrations.CreateModel(
            name='RecommendationSnapshot',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('payload', models.JSONField(default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('portfolio', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='recommendation_snapshot', to='portfolios.portfolio')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recommendation_snapshots', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-updated_at']},
        ),
    ]
