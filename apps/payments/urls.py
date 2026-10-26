"""URL routing for the payments app."""

from django.urls import path
from . import views

app_name = "payments"

urlpatterns = [
    path("create/", views.CreatePaymentView.as_view(), name="create_payment"),
    path("verify/", views.VerifyPaymentView.as_view(), name="verify_payment"),
    path("webhook/razorpay/", views.RazorpayWebhookView.as_view(), name="razorpay_webhook"),
    path("orders/<uuid:order_id>/", views.PaymentDetailView.as_view(), name="payment_detail"),
]
