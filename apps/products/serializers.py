"""Serializers for the products app."""

from rest_framework import serializers
from .models import Category, Product, ProductImage, Cart, CartItem


class CategorySerializer(serializers.ModelSerializer):
    product_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ("id", "name", "slug", "description", "image", "is_active", "product_count")

    def get_product_count(self, obj):
        return obj.products.filter(status=Product.Status.ACTIVE).count()


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ("id", "image", "alt_text", "is_primary", "sort_order")


class ProductListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for product listings."""

    category_name = serializers.CharField(source="category.name", read_only=True)
    primary_image = serializers.SerializerMethodField()
    discount_percentage = serializers.SerializerMethodField()
    is_in_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = Product
        fields = (
            "id", "name", "slug", "short_description", "sku",
            "category", "category_name", "price", "compare_at_price",
            "discount_percentage", "stock", "is_in_stock", "status",
            "is_featured", "primary_image", "created_at",
        )

    def get_primary_image(self, obj):
        img = obj.primary_image
        if img:
            request = self.context.get("request")
            return request.build_absolute_uri(img.image.url) if request else img.image.url
        return None

    def get_discount_percentage(self, obj):
        return obj.discount_percentage


class ProductDetailSerializer(serializers.ModelSerializer):
    """Full product detail serializer with all images."""

    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), source="category", write_only=True
    )
    images = ProductImageSerializer(many=True, read_only=True)
    discount_percentage = serializers.SerializerMethodField()
    is_in_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = Product
        fields = (
            "id", "name", "slug", "description", "short_description",
            "sku", "category", "category_id", "price", "compare_at_price",
            "discount_percentage", "stock", "is_in_stock", "weight",
            "status", "is_featured", "tags", "images", "created_at", "updated_at",
        )
        read_only_fields = ("id", "slug", "created_at", "updated_at")

    def get_discount_percentage(self, obj):
        return obj.discount_percentage


class CartItemSerializer(serializers.ModelSerializer):
    """Serializer for cart items."""

    product = ProductListSerializer(read_only=True)
    product_id = serializers.UUIDField(write_only=True)
    line_total = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ("id", "product", "product_id", "quantity", "line_total", "added_at")
        read_only_fields = ("id", "added_at")

    def get_line_total(self, obj):
        return str(obj.line_total)

    def validate_product_id(self, value):
        try:
            product = Product.objects.get(id=value, status=Product.Status.ACTIVE)
        except Product.DoesNotExist:
            raise serializers.ValidationError("Product not found or unavailable.")
        return value

    def validate(self, attrs):
        product_id = attrs.get("product_id")
        quantity = attrs.get("quantity", 1)
        try:
            product = Product.objects.get(id=product_id)
            if quantity > product.stock:
                raise serializers.ValidationError(
                    f"Only {product.stock} unit(s) available for '{product.name}'."
                )
        except Product.DoesNotExist:
            pass
        return attrs


class CartSerializer(serializers.ModelSerializer):
    """Shopping cart serializer."""

    items = CartItemSerializer(many=True, read_only=True)
    subtotal = serializers.SerializerMethodField()
    total_items = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ("id", "items", "total_items", "subtotal", "updated_at")

    def get_subtotal(self, obj):
        return str(obj.subtotal)

    def get_total_items(self, obj):
        return obj.total_items
