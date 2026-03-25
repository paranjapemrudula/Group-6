from rest_framework import serializers

from .models import PortfolioStock, Sector, StockUniverse


class SectorSerializer(serializers.ModelSerializer):
    universe_stock_count = serializers.IntegerField(read_only=True)
    description = serializers.CharField(read_only=True)

    class Meta:
        model = Sector
        fields = ('id', 'name', 'description', 'universe_stock_count')


class PortfolioStockSerializer(serializers.ModelSerializer):
    sector_id = serializers.PrimaryKeyRelatedField(
        source='sector',
        queryset=Sector.objects.all(),
        write_only=True,
    )
    sector_name = serializers.CharField(source='sector.name', read_only=True)

    class Meta:
        model = PortfolioStock
        fields = (
            'id',
            'symbol',
            'company_name',
            'sector_id',
            'sector_name',
            'buy_price',
            'quantity',
            'added_at',
        )
        read_only_fields = ('id', 'sector_name', 'added_at')


class StockUniverseSerializer(serializers.ModelSerializer):
    sector_name = serializers.CharField(source='sector.name', read_only=True)

    class Meta:
        model = StockUniverse
        fields = (
            'id',
            'symbol',
            'quote_symbol',
            'company_name',
            'sector_name',
            'market',
            'series',
            'isin_code',
            'source_file',
            'raw_sector_label',
            'classification_source',
            'classification_confidence',
            'weight',
            'is_active',
        )
