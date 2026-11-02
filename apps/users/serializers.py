"""Serializers for the users app."""

from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import User, Customer, Address, NewsletterSubscriber, ContactMessage


class RegisterSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""

    password = serializers.CharField(
        write_only=True, required=True, validators=[validate_password]
    )
    password2 = serializers.CharField(write_only=True, required=True, label="Confirm Password")

    class Meta:
        model = User
        fields = ("email", "first_name", "last_name", "password", "password2")

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop("password2")
        user = User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
            role=User.Role.CUSTOMER,
        )
        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom JWT serializer that includes user details in the token."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["email"] = user.email
        token["role"] = user.role
        token["full_name"] = user.full_name
        return token

    def validate(self, attrs):
        attrs["email"] = attrs["email"].strip().lower()
        data = super().validate(attrs)
        data["user"] = UserSerializer(self.user).data
        return data


class UserSerializer(serializers.ModelSerializer):
    """Public user serializer."""

    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("id", "email", "first_name", "last_name", "full_name", "role", "is_staff", "is_superuser", "date_joined")
        read_only_fields = ("id", "date_joined", "role", "is_staff", "is_superuser")

    def validate_email(self, value):
        value = value.strip().lower()
        users = User.objects.filter(email__iexact=value)
        if self.instance:
            users = users.exclude(pk=self.instance.pk)
        if users.exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def get_full_name(self, obj):
        return obj.full_name


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for password change."""

    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(
        required=True, write_only=True, validators=[validate_password]
    )
    new_password2 = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password2"]:
            raise serializers.ValidationError({"new_password": "New passwords do not match."})
        return attrs


class CustomerSerializer(serializers.ModelSerializer):
    """Customer profile serializer."""

    user = UserSerializer(read_only=True)

    class Meta:
        model = Customer
        fields = (
            "id", "user", "phone_number", "date_of_birth",
            "profile_picture", "newsletter_subscribed", "created_at",
        )
        read_only_fields = ("id", "user", "created_at")


class AddressSerializer(serializers.ModelSerializer):
    """Address serializer."""

    phone_number = serializers.RegexField(r"^\+?\d{9,15}$", max_length=17)

    class Meta:
        model = Address
        fields = (
            "id", "address_type", "full_name", "phone_number",
            "address_line1", "address_line2", "city", "state",
            "postal_code", "country", "is_default", "created_at",
        )
        read_only_fields = ("id", "created_at")

    def create(self, validated_data):
        request = self.context.get("request")
        customer, _ = Customer.objects.get_or_create(user=request.user)
        validated_data["customer"] = customer
        return super().create(validated_data)


class NewsletterSubscriptionSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(validators=[])

    class Meta:
        model = NewsletterSubscriber
        fields = ("email",)


class ContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = ("name", "email", "topic", "message")
