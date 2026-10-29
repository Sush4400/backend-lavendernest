"""
Custom User model with email-based authentication,
Customer profile, and Address models.
"""

import uuid
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.core.validators import RegexValidator


class UserManager(BaseUserManager):
    """Custom manager for email-based authentication."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email address is required.")
        email = self.normalize_email(email).strip().lower()
        extra_fields.setdefault("is_active", True)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", User.Role.ADMIN)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model using email as the unique identifier.
    Supports customer and admin roles.
    """

    class Role(models.TextChoices):
        CUSTOMER = "customer", "Customer"
        STAFF = "staff", "Staff"
        ADMIN = "admin", "Admin"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, db_index=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CUSTOMER)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ["-date_joined"]
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["role"]),
        ]

    def __str__(self):
        return self.email

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.email

    @property
    def is_customer(self):
        return self.role == self.Role.CUSTOMER

    @property
    def is_admin_user(self):
        return self.role == self.Role.ADMIN


class Customer(models.Model):
    """Extended customer profile linked to a User."""

    phone_regex = RegexValidator(
        regex=r"^\+?\d{9,15}$",
        message="Enter a valid phone number (e.g., +919876543210).",
    )

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="customer_profile"
    )
    phone_number = models.CharField(
        validators=[phone_regex], max_length=17, blank=True, default=""
    )
    date_of_birth = models.DateField(null=True, blank=True)
    profile_picture = models.ImageField(
        upload_to="customers/profiles/", null=True, blank=True
    )
    newsletter_subscribed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Customer"
        verbose_name_plural = "Customers"

    def __str__(self):
        return f"Customer: {self.user.email}"


class Address(models.Model):
    """Shipping/billing address for customers."""

    class AddressType(models.TextChoices):
        SHIPPING = "shipping", "Shipping"
        BILLING = "billing", "Billing"
        BOTH = "both", "Both"

    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name="addresses"
    )
    address_type = models.CharField(
        max_length=10, choices=AddressType.choices, default=AddressType.SHIPPING
    )
    full_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=17)
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True, default="")
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=10)
    country = models.CharField(max_length=100, default="India")
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Address"
        verbose_name_plural = "Addresses"
        ordering = ["-is_default", "-created_at"]
        indexes = [
            models.Index(fields=["customer", "is_default"]),
        ]

    def __str__(self):
        return f"{self.full_name} – {self.city}, {self.state}"

    def save(self, *args, **kwargs):
        """Ensure only one default address per customer."""
        if self.is_default:
            Address.objects.filter(
                customer=self.customer, is_default=True
            ).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)


class NewsletterSubscriber(models.Model):
    """Email subscription for the store newsletter."""

    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.email


class ContactMessage(models.Model):
    """A customer message submitted through the contact form."""

    name = models.CharField(max_length=150)
    email = models.EmailField()
    topic = models.CharField(max_length=50)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.topic}: {self.email}"
