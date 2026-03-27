from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from analysis.chatbot import generate_chatbot_reply
from analysis.services import _finbert_pipeline


class Command(BaseCommand):
    help = 'Verify LangGraph chatbot execution path and FinBERT availability.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--question',
            default='Which stock is most profitable?',
            help='Question to test through the chatbot runtime.',
        )

    def handle(self, *args, **options):
        try:
            from langgraph.graph import StateGraph  # noqa: F401

            self.stdout.write(self.style.SUCCESS('LangGraph import: OK'))
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f'LangGraph import failed: {exc}'))
            return

        finbert = _finbert_pipeline()
        if finbert is None:
            self.stdout.write(self.style.WARNING('FinBERT pipeline: unavailable or not loaded'))
        else:
            self.stdout.write(self.style.SUCCESS('FinBERT pipeline: OK'))

        user = get_user_model().objects.order_by('id').first()
        if user is None:
            self.stdout.write(self.style.WARNING('Chatbot graph test skipped: no users found in database'))
            return

        payload = generate_chatbot_reply(
            user=user,
            question=options['question'],
            history=[],
        )
        route = payload.get('route')
        model = payload.get('model')
        answer = str(payload.get('answer') or '')[:200]
        self.stdout.write(self.style.SUCCESS(f'Chatbot graph route: {route}'))
        self.stdout.write(self.style.SUCCESS(f'Chatbot model: {model}'))
        self.stdout.write(self.style.SUCCESS(f'Chatbot answer preview: {answer}'))
