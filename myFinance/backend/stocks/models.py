from django.db import models

from portfolios.models import Portfolio


class Sector(models.Model):
    name = models.CharField(max_length=80, unique=True)

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
