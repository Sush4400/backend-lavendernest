"""Filters for the products app."""

import django_filters
from .models import Product, Category


class ProductFilter(django_filters.FilterSet):
    """Advanced filtering for products."""

    category = django_filters.ModelChoiceFilter(queryset=Category.objects.filter(is_active=True))
    category_slug = django_filters.CharFilter(field_name="category__slug")
    min_price = django_filters.NumberFilter(field_name="price", lookup_expr="gte")
    max_price = django_filters.NumberFilter(field_name="price", lookup_expr="lte")
    in_stock = django_filters.BooleanFilter(method="filter_in_stock")
    is_featured = django_filters.BooleanFilter()
    status = django_filters.ChoiceFilter(choices=Product.Status.choices)

    class Meta:
        model = Product
        fields = ["category", "category_slug", "min_price", "max_price", "in_stock", "is_featured", "status"]

    def filter_in_stock(self, queryset, name, value):
        if value:
            return queryset.filter(stock__gt=0)
        return queryset.filter(stock=0)
