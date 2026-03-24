from django.db import models

from portfolios.models import Portfolio


class Sector(models.Model):
    name = models.CharField(max_length=80, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class PortfolioStock(models.Model):
    portfolio = models.ForeignKey(
        Portfolio,
        on_delete=models.CASCADE,
        related_name='stocks',
    )
    symbol = models.CharField(max_length=20)
    company_name = models.CharField(max_length=200)
    sector = models.ForeignKey(
        Sector,
        on_delete=models.PROTECT,
        related_name='portfolio_stocks',
    )
    buy_price = models.DecimalField(max_digits=12, decimal_places=2)
    quantity = models.PositiveIntegerField()
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-added_at']

    def __str__(self):
        return f'{self.symbol} - {self.portfolio.name}'


class StockUniverse(models.Model):
    CLASSIFICATION_RULE = 'RULE'
    CLASSIFICATION_ALIAS = 'ALIAS'
    CLASSIFICATION_VECTOR = 'VECTOR'
    CLASSIFICATION_MANUAL = 'MANUAL'
    CLASSIFICATION_UNKNOWN = 'UNKNOWN'
    CLASSIFICATION_CHOICES = [
        (CLASSIFICATION_RULE, 'Rule Based'),
        (CLASSIFICATION_ALIAS, 'Alias Match'),
        (CLASSIFICATION_VECTOR, 'Vector Match'),
        (CLASSIFICATION_MANUAL, 'Manual'),
        (CLASSIFICATION_UNKNOWN, 'Unknown'),
    ]

    MARKET_INDIA = 'INDIA'
    MARKET_USA = 'USA'
    MARKET_CHOICES = [
        (MARKET_INDIA, 'India'),
        (MARKET_USA, 'USA'),
    ]

    symbol = models.CharField(max_length=32)
    company_name = models.CharField(max_length=255)
    sector = models.ForeignKey(
        Sector,
        on_delete=models.PROTECT,
        related_name='universe_stocks',
    )
    raw_sector_label = models.CharField(max_length=255, blank=True)
    market = models.CharField(max_length=16, choices=MARKET_CHOICES)
    series = models.CharField(max_length=32, blank=True)
    isin_code = models.CharField(max_length=32, blank=True)
    source_file = models.CharField(max_length=255, blank=True)
    classification_source = models.CharField(
        max_length=16,
        choices=CLASSIFICATION_CHOICES,
        default=CLASSIFICATION_UNKNOWN,
    )
    classification_confidence = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['market', 'company_name']
        unique_together = [('symbol', 'market')]

    def __str__(self):
        return f'{self.symbol} ({self.market})'


class SectorAlias(models.Model):
    sector = models.ForeignKey(
        Sector,
        on_delete=models.CASCADE,
        related_name='aliases',
    )
    alias_name = models.CharField(max_length=120, unique=True)

    class Meta:
        ordering = ['alias_name']

    def __str__(self):
        return f'{self.alias_name} -> {self.sector.name}'


class SectorClassificationLog(models.Model):
    stock_symbol = models.CharField(max_length=32)
    company_name = models.CharField(max_length=255, blank=True)
    market = models.CharField(max_length=16, blank=True)
    raw_label = models.CharField(max_length=255, blank=True)
    predicted_sector = models.ForeignKey(
        Sector,
        on_delete=models.PROTECT,
        related_name='classification_logs',
    )
    classification_source = models.CharField(max_length=16, choices=StockUniverse.CLASSIFICATION_CHOICES)
    confidence = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.stock_symbol} -> {self.predicted_sector.name}'
