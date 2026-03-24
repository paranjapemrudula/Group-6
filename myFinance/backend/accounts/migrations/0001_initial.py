from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='SecurityQuestion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('question_text', models.CharField(max_length=255, unique=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
<<<<<<< HEAD
            options={
                'ordering': ['id'],
            },
=======
            options={'ordering': ['id']},
>>>>>>> 976cc83ad358ca0afbd53314dddde500db23c137
        ),
        migrations.CreateModel(
            name='PasswordResetSession',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token', models.CharField(max_length=128, unique=True)),
                ('method', models.CharField(choices=[('totp', 'Authenticator'), ('fallback', 'Fallback')], max_length=20)),
                ('is_used', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('expires_at', models.DateTimeField()),
<<<<<<< HEAD
                (
                    'user',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='password_reset_sessions',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                'ordering': ['-created_at'],
            },
=======
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='password_reset_sessions', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at']},
>>>>>>> 976cc83ad358ca0afbd53314dddde500db23c137
        ),
        migrations.CreateModel(
            name='RecoveryCode',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code_hash', models.CharField(max_length=128)),
                ('is_used', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('used_at', models.DateTimeField(blank=True, null=True)),
<<<<<<< HEAD
                (
                    'user',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='recovery_codes',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                'ordering': ['-created_at'],
            },
=======
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recovery_codes', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at']},
>>>>>>> 976cc83ad358ca0afbd53314dddde500db23c137
        ),
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('phone_number', models.CharField(blank=True, max_length=32)),
                ('totp_enabled', models.BooleanField(default=False)),
                ('totp_secret', models.CharField(blank=True, max_length=64)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
<<<<<<< HEAD
                (
                    'user',
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='profile',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                'ordering': ['user__username'],
            },
=======
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='profile', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['user__username']},
>>>>>>> 976cc83ad358ca0afbd53314dddde500db23c137
        ),
        migrations.CreateModel(
            name='UserSecurityAnswer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('answer_hash', models.CharField(max_length=128)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
<<<<<<< HEAD
                (
                    'question',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='user_answers',
                        to='accounts.securityquestion',
                    ),
                ),
                (
                    'user',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='security_answers',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                'ordering': ['question_id'],
                'unique_together': {('user', 'question')},
            },
=======
                ('question', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_answers', to='accounts.securityquestion')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='security_answers', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['question_id'], 'unique_together': {('user', 'question')}},
>>>>>>> 976cc83ad358ca0afbd53314dddde500db23c137
        ),
    ]
