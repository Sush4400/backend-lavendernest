"""Serializers for the products app."""

from rest_framework import serializers
from .models import Category, Product, ProductImage, Cart, CartItem, WishlistItem


CURATED_PRODUCT_IMAGES = {
    "lavender-dreams-candle": "https://images.unsplash.com/photo-1603006905003-be475563bc59?auto=format&fit=crop&w=800&q=80",
    "rose-garden-candle": "https://images.unsplash.com/photo-1508746829417-e6f548d8d6ed?auto=format&fit=crop&w=800&q=80",
    "vanilla-sky-soy-candle": "https://images.unsplash.com/photo-1572726729207-a78d6feb18d7?auto=format&fit=crop&w=800&q=80",
    "ocean-breeze-mini-candle-set": "https://images.unsplash.com/photo-1517841905240-472988babdf9?auto=format&fit=crop&w=800&q=80",
    "midnight-jasmine-candle": "https://images.unsplash.com/photo-1596433809252-260c2745dfdd?auto=format&fit=crop&w=800&q=80",
    "blush-rose-bouquet": "https://images.unsplash.com/photo-1563241527-3004b7be0ffd?auto=format&fit=crop&w=800&q=80",
    "sunflower-sunshine-bunch": "https://images.unsplash.com/photo-1597848212624-a19eb35e2651?auto=format&fit=crop&w=800&q=80",
    "wildflower-meadow-arrangement": "https://images.unsplash.com/photo-1490750967868-88aa4486c946?auto=format&fit=crop&w=800&q=80",
    "pastel-rainbow-mini-bouquet": "https://images.unsplash.com/photo-1526047932273-341f2a7631f9?auto=format&fit=crop&w=800&q=80",
    "vintage-amber-fairy-light-bottle": "https://images.unsplash.com/photo-1517457373958-b7bdd4587205?auto=format&fit=crop&w=800&q=80",
    "clear-glass-star-light-bottle": "https://images.unsplash.com/photo-1544816155-12df9643f363?auto=format&fit=crop&w=800&q=80",
    "frosted-globe-petal-light-bottle": "https://images.unsplash.com/photo-1513519245088-0e12902e5a38?auto=format&fit=crop&w=800&q=80",
    "recycled-bottle-cluster-set": "https://images.unsplash.com/photo-1509198397868-475647b2a1e5?auto=format&fit=crop&w=800&q=80",
}

def get_product_fallback_image(obj):
    if hasattr(obj, "details") and isinstance(obj.details, dict) and obj.details.get("image_url"):
        return obj.details["image_url"]
    if obj.slug in CURATED_PRODUCT_IMAGES:
        return CURATED_PRODUCT_IMAGES[obj.slug]
    cat_slug = obj.category.slug if obj.category else ""
    if "candle" in cat_slug:
        return "https://images.unsplash.com/photo-1603006905003-be475563bc59?auto=format&fit=crop&w=800&q=80"
    if "flower" in cat_slug:
        return "https://images.unsplash.com/photo-1563241527-3004b7be0ffd?auto=format&fit=crop&w=800&q=80"
    return "https://images.unsplash.com/photo-1517457373958-b7bdd4587205?auto=format&fit=crop&w=800&q=80"


class CategorySerializer(serializers.ModelSerializer):
    product_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ("id", "name", "slug", "description", "image", "is_active", "product_count")

    def get_product_count(self, obj):
        if hasattr(obj, "active_product_count"):
            return obj.active_product_count
        return obj.products.filter(status=Product.Status.ACTIVE).count()

    # def to_representation(self, instance):
    #     ret = super().to_representation(instance)
    #     if not ret.get("image"):
    #         defaults = {
    #             "candles": "https://images.unsplash.com/photo-1603006905003-be475563bc59?auto=format&fit=crop&w=800&q=80",
    #             "pipe-cleaner-flowers": "https://images.unsplash.com/photo-1563241527-3004b7be0ffd?auto=format&fit=crop&w=800&q=80",
    #             "light-bottles": "https://images.unsplash.com/photo-1517457373958-b7bdd4587205?auto=format&fit=crop&w=800&q=80",
    #         }
    #         ret["image"] = defaults.get(
    #             instance.slug,
    #             "https://images.unsplash.com/photo-1603006905003-be475563bc59?auto=format&fit=crop&w=800&q=80"
    #         )
    #     return ret


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
            "is_featured", "primary_image", "subcategory", "tags", "created_at",
        )

    def get_primary_image(self, obj):
        img = obj.primary_image
        if img and img.image:
            try:
                request = self.context.get("request")
                return request.build_absolute_uri(img.image.url) if request else img.image.url
            except Exception:
                pass
        return get_product_fallback_image(obj)

    def get_discount_percentage(self, obj):
        return obj.discount_percentage


class ProductDetailSerializer(serializers.ModelSerializer):
    """Full product detail serializer with all images."""

    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), source="category", write_only=True,
        required=False, allow_null=True
    )
    images = ProductImageSerializer(many=True, read_only=True)
    primary_image = serializers.SerializerMethodField()
    discount_percentage = serializers.SerializerMethodField()
    is_in_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = Product
        fields = (
            "id", "name", "slug", "description", "short_description",
            "sku", "category", "category_id", "price", "compare_at_price",
            "discount_percentage", "stock", "is_in_stock", "weight",
            "status", "is_featured", "primary_image", "tags", "subcategory", "details",
            "care_instructions", "shipping_info", "images", "created_at", "updated_at",
        )
        read_only_fields = ("id", "slug", "created_at", "updated_at")

    def get_primary_image(self, obj):
        img = obj.primary_image
        if img and img.image:
            try:
                request = self.context.get("request")
                return request.build_absolute_uri(img.image.url) if request else img.image.url
            except Exception:
                pass
        return get_product_fallback_image(obj)

    def get_discount_percentage(self, obj):
        return obj.discount_percentage

    # def to_representation(self, instance):
    #     ret = super().to_representation(instance)
    #     if not ret.get("images"):
    #         primary = ret.get("primary_image")
    #         if primary:
    #             ret["images"] = [
    #                 {"id": 1, "image": primary, "alt_text": instance.name, "is_primary": True, "sort_order": 0}
    #             ]
    #     return ret


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
            if product.status != Product.Status.ACTIVE:
                raise serializers.ValidationError("Product is no longer available.")
            if quantity > product.stock:
                raise serializers.ValidationError(
                    f"Only {product.stock} unit(s) available for '{product.name}'."
                )
        except Product.DoesNotExist:
            pass
        return attrs


class CartQuantitySerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1)


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


class WishlistItemSerializer(serializers.ModelSerializer):
    product = ProductListSerializer(read_only=True)
    product_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = WishlistItem
        fields = ("id", "product", "product_id", "created_at")
        read_only_fields = ("id", "created_at")

    def validate_product_id(self, value):
        if not Product.objects.filter(pk=value, status=Product.Status.ACTIVE).exists():
            raise serializers.ValidationError("Product not found or unavailable.")
        return value

    def create(self, validated_data):
        customer = self.context["request"].user.customer_profile
        item, _ = WishlistItem.objects.get_or_create(
            customer=customer, product_id=validated_data["product_id"]
        )
        return item
