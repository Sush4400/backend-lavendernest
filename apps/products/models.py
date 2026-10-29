"""
Product catalog models: Category, Product, ProductImage, Cart, CartItem.
"""

import uuid
from django.db import models
from django.core.validators import MinValueValidator
from django.utils.text import slugify
from apps.users.models import Customer


def category_image_path(instance, filename):
    return f"categories/{instance.slug}/{filename}"


def product_image_path(instance, filename):
    return f"products/{instance.product.slug}/{filename}"


class Category(models.Model):
    """Product categories (e.g., Candles, Flowers, Home Decor)."""

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True, default="")
    image = models.ImageField(upload_to=category_image_path, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Product(models.Model):
    """Handcrafted product listings."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        DISCONTINUED = "discontinued", "Discontinued"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, db_index=True)
    slug = models.SlugField(max_length=280, unique=True, blank=True)
    description = models.TextField()
    short_description = models.CharField(max_length=500, blank=True, default="")
    care_instructions = models.TextField(blank=True, default="")
    shipping_info = models.TextField(blank=True, default="")
    details = models.JSONField(default=dict, blank=True)
    subcategory = models.CharField(max_length=50, blank=True, default="", db_index=True)
    sku = models.CharField(max_length=100, unique=True)
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, related_name="products"
    )
    price = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0)]
    )
    compare_at_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0)],
        help_text="Original price (for discount display)"
    )
    stock = models.PositiveIntegerField(default=0)
    weight = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True,
        help_text="Weight in grams"
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    is_featured = models.BooleanField(default=False)
    tags = models.CharField(max_length=500, blank=True, default="", help_text="Comma-separated tags")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Product"
        verbose_name_plural = "Products"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "category"]),
            models.Index(fields=["sku"]),
            models.Index(fields=["is_featured"]),
            models.Index(fields=["price"]),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            self.slug = f"{base_slug}-{str(self.id)[:8]}"
        super().save(*args, **kwargs)

    @property
    def is_in_stock(self):
        return self.stock > 0

    @property
    def discount_percentage(self):
        if self.compare_at_price and self.compare_at_price > self.price:
            discount = ((self.compare_at_price - self.price) / self.compare_at_price) * 100
            return round(discount, 1)
        return None

    @property
    def primary_image(self):
        return self.images.filter(is_primary=True).first() or self.images.first()


class ProductImage(models.Model):
    """Multiple images per product."""

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField(upload_to=product_image_path)
    alt_text = models.CharField(max_length=255, blank=True, default="")
    is_primary = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Product Image"
        verbose_name_plural = "Product Images"
        ordering = ["sort_order", "-is_primary"]

    def __str__(self):
        return f"Image for {self.product.name}"

    def save(self, *args, **kwargs):
        if self.is_primary:
            ProductImage.objects.filter(
                product=self.product, is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)


class Cart(models.Model):
    """Shopping cart associated with a customer or session."""

    customer = models.OneToOneField(
        Customer, on_delete=models.CASCADE, related_name="cart", null=True, blank=True
    )
    session_key = models.CharField(max_length=40, null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Cart"
        verbose_name_plural = "Carts"
        constraints = [
            models.UniqueConstraint(
                fields=["session_key"],
                condition=models.Q(session_key__isnull=False),
                name="unique_session_shopping_cart",
            )
        ]

    def __str__(self):
        if self.customer:
            return f"Cart of {self.customer.user.email}"
        return f"Anonymous Cart ({self.session_key})"

    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())

    @property
    def subtotal(self):
        return sum(item.line_total for item in self.items.all())


class CartItem(models.Model):
    """Individual item in a shopping cart."""

    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Cart Item"
        verbose_name_plural = "Cart Items"
        unique_together = ("cart", "product")

    def __str__(self):
        return f"{self.quantity}× {self.product.name}"

    @property
    def line_total(self):
        return self.product.price * self.quantity

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.quantity > self.product.stock:
            raise ValidationError(
                f"Only {self.product.stock} units of '{self.product.name}' available."
            )


class WishlistItem(models.Model):
    """A product saved by a customer."""

    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name="wishlist_items"
    )
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="wishlisted_by"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["customer", "product"], name="unique_customer_wishlist_product"
            )
        ]

    def __str__(self):
        return f"{self.customer.user.email}: {self.product.name}"
