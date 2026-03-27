from django.core.management.base import BaseCommand

from analysis.models import ChatKnowledgeDocument, ChatPromptVersion


PROMPT_DEFAULTS = {
    'name': 'finance_chatbot',
    'version': 3,
    'description': 'Evidence-based finance analysis assistant prompt.',
    'instructions': (
        'You are a finance analysis assistant for a portfolio web application. '
        'Your job is to answer user investment questions using actual portfolio data, live market data, sentiment analysis, and forecasting outputs. '
        'Do not guess financial values. Always use portfolio records and live market data before answering. '
        'For profit and loss questions, calculate invested amount, current value, profit or loss, and return percentage. '
        'For best and worst investment questions, rank holdings by return percentage and total gain or loss. '
        'For diversification questions, analyze sector allocation and concentration risk. '
        'For sentiment questions, use recent financial news sentiment scores and summarize whether sentiment is positive, negative, or neutral. '
        'For forecasting questions, use forecasting output and clearly state that predictions are probabilistic, not guaranteed. '
        'For recommendation questions, combine profitability, sentiment, forecast, and risk signals before suggesting hold, buy, sell, or rebalance. '
        'Always explain the reason behind the answer in simple language. If data is missing, state what data is unavailable instead of inventing an answer. '
        'Keep responses clear, investment-focused, and based on evidence.'
    ),
    'routing_config': {
        'top_questions': [
            'Which stocks or assets are generating the highest returns in my portfolio?',
            'Which investments are consistently underperforming or causing losses?',
            'Is my portfolio well diversified across sectors and asset types?',
            'What is the risk level of my portfolio based on volatility and drawdown?',
            'What is the current market sentiment for my invested stocks?',
            'What are the top 3 better investment options based on my current portfolio?',
            'Should I hold, buy more, or sell my current investments based on market conditions?',
            'What would be my portfolio value after 1 year if current trends continue?',
            'What is the probability of loss in my portfolio?',
            'Which sector should I invest in right now?',
        ],
    },
}

DOCUMENT_DEFAULTS = [
    {
        'title': 'Highest Returns Intent',
        'slug': 'highest-returns-intent',
        'category': 'highest_returns',
        'source_type': 'portfolio',
        'content': (
            'When the user asks about highest returns, compare live current price versus buy price for each holding. '
            'Rank holdings by return percentage and unrealized gain, and answer with the top performers in a readable summary.'
        ),
        'keywords': ['highest returns', 'top performers', 'best returns', 'portfolio gain'],
    },
    {
        'title': 'Underperformers Intent',
        'slug': 'underperformers-intent',
        'category': 'underperformers',
        'source_type': 'portfolio',
        'content': (
            'When the user asks about losses or underperformers, identify holdings with negative return percentages or negative unrealized P and L. '
            'Explain which positions are dragging performance and keep the answer factual.'
        ),
        'keywords': ['underperforming', 'losses', 'worst stock', 'negative return'],
    },
    {
        'title': 'Diversification Intent',
        'slug': 'diversification-intent',
        'category': 'diversification',
        'source_type': 'portfolio',
        'content': (
            'When the user asks about diversification, measure concentration by sector weights and explain whether the portfolio is highly concentrated, somewhat concentrated, or diversified. '
            'Mention that the app mainly tracks equity holdings, so sector spread is the key diversification signal.'
        ),
        'keywords': ['diversification', 'sector allocation', 'asset types', 'concentration'],
    },
    {
        'title': 'Risk Level Intent',
        'slug': 'risk-level-intent',
        'category': 'risk_level',
        'source_type': 'portfolio',
        'content': (
            'When the user asks about risk level, use volatility and drawdown from historical price series. '
            'Translate those values into low, moderate, or high risk with a plain-language explanation.'
        ),
        'keywords': ['risk', 'volatility', 'drawdown', 'portfolio risk'],
    },
    {
        'title': 'Market Sentiment Intent',
        'slug': 'market-sentiment-intent',
        'category': 'market_sentiment',
        'source_type': 'market',
        'content': (
            'When the user asks about bullish or bearish conditions, use recent news sentiment and live direction across invested stocks. '
            'Summarize whether the tone is bullish, bearish, or mixed.'
        ),
        'keywords': ['sentiment', 'bullish', 'bearish', 'market mood'],
    },
    {
        'title': 'Better Options Intent',
        'slug': 'better-options-intent',
        'category': 'better_options',
        'source_type': 'guide',
        'content': (
            'When the user asks for better options, favor underweight sectors and combine simple valuation signals like discount ratio and reasonable P E ratio. '
            'Present the top three ideas with a concise reason.'
        ),
        'keywords': ['better options', 'top 3', 'investment ideas', 'alternatives'],
    },
    {
        'title': 'Hold Buy Sell Intent',
        'slug': 'hold-buy-sell-intent',
        'category': 'hold_buy_sell',
        'source_type': 'guide',
        'content': (
            'When the user asks whether to hold, buy more, or sell, use the app recommendation score together with sentiment, price direction, and concentration. '
            'Group current holdings into buy more, hold, and reduce or watch buckets.'
        ),
        'keywords': ['hold', 'buy more', 'sell', 'recommendation'],
    },
    {
        'title': 'One Year Forecast Intent',
        'slug': 'one-year-forecast-intent',
        'category': 'forecast_one_year',
        'source_type': 'guide',
        'content': (
            'When the user asks about portfolio value after one year, provide a scenario based on current trend continuation using historical return behavior. '
            'State clearly that it is a scenario, not a guaranteed forecast.'
        ),
        'keywords': ['1 year value', 'forecast', 'one year', 'future value'],
    },
    {
        'title': 'Loss Probability Intent',
        'slug': 'loss-probability-intent',
        'category': 'loss_probability',
        'source_type': 'guide',
        'content': (
            'When the user asks about probability of loss, estimate it from the frequency of negative historical returns and explain that it reflects recent behavior rather than certainty.'
        ),
        'keywords': ['probability of loss', 'chance of loss', 'risk of losing'],
    },
    {
        'title': 'Best Sector Intent',
        'slug': 'best-sector-intent',
        'category': 'best_sector_now',
        'source_type': 'market',
        'content': (
            'When the user asks which sector to invest in, compare sector-level valuation and discount support from the available market universe. '
            'Return the strongest sector with a clear but non-certain explanation.'
        ),
        'keywords': ['best sector', 'sector now', 'where to invest'],
    },
]


class Command(BaseCommand):
    help = 'Seed active prompt version and starter knowledge documents for the chatbot.'

    def handle(self, *args, **options):
        ChatPromptVersion.objects.filter(name=PROMPT_DEFAULTS['name']).exclude(version=PROMPT_DEFAULTS['version']).update(
            is_active=False
        )
        prompt, prompt_created = ChatPromptVersion.objects.update_or_create(
            name=PROMPT_DEFAULTS['name'],
            version=PROMPT_DEFAULTS['version'],
            defaults={
                'description': PROMPT_DEFAULTS['description'],
                'instructions': PROMPT_DEFAULTS['instructions'],
                'routing_config': PROMPT_DEFAULTS['routing_config'],
                'is_active': True,
            },
        )

        created_count = 0
        for document in DOCUMENT_DEFAULTS:
            _, created = ChatKnowledgeDocument.objects.update_or_create(
                slug=document['slug'],
                defaults=document,
            )
            if created:
                created_count += 1

        action_text = 'created' if prompt_created else 'updated'
        self.stdout.write(self.style.SUCCESS(f'Prompt {prompt.name} v{prompt.version} {action_text}.'))
        self.stdout.write(self.style.SUCCESS(f'Starter knowledge documents created or updated: {len(DOCUMENT_DEFAULTS)}.'))
        self.stdout.write(self.style.SUCCESS(f'New documents created in this run: {created_count}.'))
