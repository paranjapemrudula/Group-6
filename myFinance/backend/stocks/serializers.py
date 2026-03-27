from rest_framework import serializers

from .models import PortfolioStock, Sector, StockUniverse


def _infer_sector(*, attrs, instance=None):
    sector = attrs.get('sector')
    if sector is not None:
        return sector

    symbol = attrs.get('symbol')
    company_name = attrs.get('company_name')

    if instance is not None:
        symbol = symbol or instance.symbol
        company_name = company_name or instance.company_name

    if symbol:
        universe_stock = (
            StockUniverse.objects.filter(symbol__iexact=symbol.strip(), is_active=True)
            .select_related('sector')
            .order_by('market', 'company_name')
            .first()
        )
        if universe_stock:
            return universe_stock.sector

    if company_name:
        universe_stock = (
            StockUniverse.objects.filter(company_name__iexact=company_name.strip(), is_active=True)
            .select_related('sector')
            .first()
        )
        if universe_stock:
            return universe_stock.sector

    return Sector.objects.order_by('name').first()


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
        required=False,
        allow_null=True,
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

    def validate(self, attrs):
        sector = _infer_sector(attrs=attrs, instance=getattr(self, 'instance', None))
        if sector is None:
            raise serializers.ValidationError(
                {'sector_id': 'No sector could be resolved. Please import sectors or provide a valid stock mapping first.'}
            )
        attrs['sector'] = sector
        return attrs


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
