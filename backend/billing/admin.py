"""
Billing admin configuration.
"""
from django.contrib import admin
from .models import BillingPlan, Subscription, UsageLog, Invoice


@admin.register(BillingPlan)
class BillingPlanAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'plan_type',
        'price_monthly',
        'price_yearly',
        'max_workspaces',
        'max_channels',
        'max_messages_per_month',
        'is_active',
        'is_default',
    ]
    list_filter = ['plan_type', 'is_active', 'is_default']
    search_fields = ['name']


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = [
        'user',
        'plan',
        'interval',
        'status',
        'current_period_end',
        'cancel_at_period_end',
    ]
    list_filter = ['status', 'interval', 'plan']
    search_fields = ['user__email', 'stripe_subscription_id']
    readonly_fields = [
        'stripe_subscription_id',
        'stripe_customer_id',
        'current_period_start',
        'current_period_end',
    ]


@admin.register(UsageLog)
class UsageLogAdmin(admin.ModelAdmin):
    list_display = [
        'workspace',
        'date',
        'message_count',
        'token_count_input',
        'token_count_output',
        'estimated_cost',
    ]
    list_filter = ['date']
    search_fields = ['workspace__name']
    date_hierarchy = 'date'


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = [
        'stripe_invoice_id',
        'subscription',
        'amount_due',
        'amount_paid',
        'status',
        'created_at',
    ]
    list_filter = ['status', 'created_at']
    search_fields = ['stripe_invoice_id', 'subscription__user__email']
    readonly_fields = ['stripe_invoice_id']
