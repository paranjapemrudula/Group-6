from rest_framework import serializers

from .models import PortfolioStock, Sector


class SectorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sector
        fields = ('id', 'name')


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
