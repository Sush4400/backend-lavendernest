"""Signals for the users app – auto-create Customer profile on user creation."""

import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, Customer

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def create_customer_profile(sender, instance, created, **kwargs):
    """Automatically create a Customer profile when a new user registers."""
    if created and instance.role == User.Role.CUSTOMER:
        Customer.objects.get_or_create(user=instance)
        logger.info("Customer profile created for user: %s", instance.email)
