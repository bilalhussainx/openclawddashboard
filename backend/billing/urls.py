"""
Billing URL configuration.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from . import webhooks

app_name = 'billing'

router = DefaultRouter()
router.register(r'plans', views.BillingPlanViewSet, basename='plan')

urlpatterns = [
    path('', include(router.urls)),
    path('subscription/', views.get_subscription, name='subscription'),
    path('checkout/', views.create_checkout_session, name='checkout'),
    path('portal/', views.create_portal_session, name='portal'),
    path('cancel/', views.cancel_subscription, name='cancel'),
    path('usage/', views.get_usage_summary, name='usage'),
    path('invoices/', views.get_invoices, name='invoices'),
    path('webhook/', webhooks.stripe_webhook, name='webhook'),
]
