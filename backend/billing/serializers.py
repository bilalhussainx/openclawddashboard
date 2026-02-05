"""
Billing serializers.
"""
from rest_framework import serializers
from .models import BillingPlan, Subscription, UsageLog, Invoice


class BillingPlanSerializer(serializers.ModelSerializer):
    """Serializer for BillingPlan model."""

    class Meta:
        model = BillingPlan
        fields = [
            'id',
            'name',
            'plan_type',
            'description',
            'price_monthly',
            'price_yearly',
            'max_workspaces',
            'max_channels',
            'max_messages_per_month',
            'max_skills',
            'allowed_models',
            'features',
            'is_active',
        ]


class SubscriptionSerializer(serializers.ModelSerializer):
    """Serializer for Subscription model."""
    plan = BillingPlanSerializer(read_only=True)
    plan_id = serializers.IntegerField(write_only=True, required=False)
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = Subscription
        fields = [
            'id',
            'plan',
            'plan_id',
            'interval',
            'status',
            'current_period_start',
            'current_period_end',
            'cancel_at_period_end',
            'is_active',
            'created_at',
        ]
        read_only_fields = [
            'id',
            'status',
            'current_period_start',
            'current_period_end',
            'created_at',
        ]


class UsageLogSerializer(serializers.ModelSerializer):
    """Serializer for UsageLog model."""
    workspace_name = serializers.CharField(source='workspace.name', read_only=True)
    total_tokens = serializers.IntegerField(read_only=True)

    class Meta:
        model = UsageLog
        fields = [
            'id',
            'workspace',
            'workspace_name',
            'date',
            'message_count',
            'token_count_input',
            'token_count_output',
            'total_tokens',
            'estimated_cost',
            'model_usage',
        ]


class InvoiceSerializer(serializers.ModelSerializer):
    """Serializer for Invoice model."""

    class Meta:
        model = Invoice
        fields = [
            'id',
            'stripe_invoice_id',
            'amount_due',
            'amount_paid',
            'currency',
            'status',
            'hosted_invoice_url',
            'invoice_pdf',
            'period_start',
            'period_end',
            'created_at',
            'paid_at',
        ]


class CreateCheckoutSessionSerializer(serializers.Serializer):
    """Serializer for creating a Stripe checkout session."""
    plan_id = serializers.IntegerField()
    interval = serializers.ChoiceField(choices=['monthly', 'yearly'])
    success_url = serializers.URLField()
    cancel_url = serializers.URLField()


class UsageSummarySerializer(serializers.Serializer):
    """Serializer for usage summary."""
    total_messages = serializers.IntegerField()
    total_tokens = serializers.IntegerField()
    total_cost = serializers.DecimalField(max_digits=10, decimal_places=2)
    period_start = serializers.DateField()
    period_end = serializers.DateField()
    daily_usage = UsageLogSerializer(many=True)
