from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('analysis', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ChatKnowledgeDocument',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=160)),
                ('slug', models.SlugField(max_length=180, unique=True)),
                ('category', models.CharField(default='guide', max_length=40)),
                ('source_type', models.CharField(choices=[('system', 'System'), ('faq', 'FAQ'), ('market', 'Market'), ('portfolio', 'Portfolio'), ('guide', 'Guide')], default='guide', max_length=20)),
                ('content', models.TextField()),
                ('keywords', models.JSONField(blank=True, default=list)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['title'],
            },
        ),
        migrations.CreateModel(
            name='ChatPromptVersion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=80)),
                ('version', models.PositiveIntegerField()),
                ('description', models.CharField(blank=True, max_length=255)),
                ('instructions', models.TextField()),
                ('routing_config', models.JSONField(blank=True, default=dict)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['name', '-version'],
                'unique_together': {('name', 'version')},
            },
        ),
        migrations.CreateModel(
            name='ChatInteractionLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('question', models.TextField()),
                ('answer', models.TextField()),
                ('category', models.CharField(default='finance', max_length=40)),
                ('route', models.CharField(default='general', max_length=40)),
                ('model', models.CharField(default='local-rag', max_length=80)),
                ('prompt_name', models.CharField(blank=True, max_length=80)),
                ('prompt_version', models.PositiveIntegerField(default=1)),
                ('retrieval_count', models.PositiveIntegerField(default=0)),
                ('confidence', models.FloatField(default=0.0)),
                ('used_documents', models.JSONField(blank=True, default=list)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='chat_interactions', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
