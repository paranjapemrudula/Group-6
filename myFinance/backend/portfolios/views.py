from rest_framework import generics

from .models import Portfolio
from .serializers import PortfolioSerializer


class PortfolioListCreateView(generics.ListCreateAPIView):
    serializer_class = PortfolioSerializer

    def get_queryset(self):
        return Portfolio.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class PortfolioDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = PortfolioSerializer
    lookup_url_kwarg = 'id'

    def get_queryset(self):
        return Portfolio.objects.filter(user=self.request.user)

# Create your views here.
