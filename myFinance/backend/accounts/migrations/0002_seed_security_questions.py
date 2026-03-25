from django.db import migrations


DEFAULT_SECURITY_QUESTIONS = [
    'What was the name of your first school?',
    'What is your mother’s birth city?',
    'What was your childhood nickname?',
    'What is the name of your favorite teacher?',
]


def seed_security_questions(apps, schema_editor):
    SecurityQuestion = apps.get_model('accounts', 'SecurityQuestion')
    for question_text in DEFAULT_SECURITY_QUESTIONS:
        SecurityQuestion.objects.get_or_create(
            question_text=question_text,
            defaults={'is_active': True},
        )


def unseed_security_questions(apps, schema_editor):
    SecurityQuestion = apps.get_model('accounts', 'SecurityQuestion')
    SecurityQuestion.objects.filter(question_text__in=DEFAULT_SECURITY_QUESTIONS).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_security_questions, unseed_security_questions),
    ]
