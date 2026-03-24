from django.contrib import admin

from .models import PortfolioStock, Sector, SectorAlias, SectorClassificationLog, StockUniverse


@admin.register(Sector)
class SectorAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)


@admin.register(StockUniverse)
class StockUniverseAdmin(admin.ModelAdmin):
    list_display = (
        'symbol',
        'company_name',
        'sector',
        'market',
        'classification_source',
        'classification_confidence',
        'source_file',
        'is_active',
    )
    list_filter = ('market', 'sector', 'classification_source', 'is_active')
    search_fields = ('symbol', 'company_name', 'isin_code', 'raw_sector_label')


@admin.register(PortfolioStock)
class PortfolioStockAdmin(admin.ModelAdmin):
    list_display = ('symbol', 'company_name', 'portfolio', 'sector', 'quantity', 'buy_price', 'added_at')
    list_filter = ('sector', 'portfolio')
    search_fields = ('symbol', 'company_name', 'portfolio__name')


@admin.register(SectorAlias)
class SectorAliasAdmin(admin.ModelAdmin):
    list_display = ('alias_name', 'sector')
    list_filter = ('sector',)
    search_fields = ('alias_name', 'sector__name')


@admin.register(SectorClassificationLog)
class SectorClassificationLogAdmin(admin.ModelAdmin):
    list_display = (
        'stock_symbol',
        'company_name',
        'market',
        'predicted_sector',
        'classification_source',
        'confidence',
        'created_at',
    )
    list_filter = ('market', 'predicted_sector', 'classification_source')
    search_fields = ('stock_symbol', 'company_name', 'raw_label', 'notes')
