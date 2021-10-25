# views.py
from rest_framework import viewsets

from .serializers import SiteSerializer, PageSerializer, PageChangeSerializer
from .models import Site, Page, PageChange

class SiteViewSet(viewsets.ModelViewSet):
    queryset = Site.objects.all().order_by('site_id')
    serializer_class = SiteSerializer

class PageViewSet(viewsets.ModelViewSet):
    queryset = Page.objects.all().order_by('page_id')
    serializer_class = PageSerializer

class PageChangeViewSet(viewsets.ModelViewSet):
    queryset = PageChange.objects.all().order_by('created_at')
    serializer_class = PageChangeSerializer