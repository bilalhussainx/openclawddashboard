"""
Billing models - Plans, subscriptions, and usage tracking.
"""
from django.db import models
from django.conf import settings
from decimal import Decimal


class BillingPlan(models.Model):
    """Available billing plans."""

    class PlanType(models.TextChoices):
        FREE = 'free', 'Free'
        PRO = 'pro', 'Pro'
        ENTERPRISE = 'enterprise', 'Enterprise'

    name = models.CharField(max_length=50)
    plan_type = models.CharField(
        max_length=20,
        choices=PlanType.choices,
        unique=True
    )
    description = models.TextField(blank=True)

    # Pricing
    price_monthly = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    price_yearly = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )

    # Limits
    max_workspaces = models.IntegerField(default=1)
    max_channels = models.IntegerField(default=1)
    max_messages_per_month = models.IntegerField(default=1000)
    max_skills = models.IntegerField(default=5)

    # Features
    allowed_models = models.JSONField(
        default=list,
        help_text='List of allowed model identifiers'
    )
    features = models.JSONField(
        default=list,
        help_text='List of feature descriptions'
    )

    # Stripe
    stripe_price_id_monthly = models.CharField(max_length=100, blank=True)
    stripe_price_id_yearly = models.CharField(max_length=100, blank=True)
    stripe_product_id = models.CharField(max_length=100, blank=True)

    # Status
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['price_monthly']
        verbose_name = 'Billing Plan'
        verbose_name_plural = 'Billing Plans'

    def __str__(self):
        return f"{self.name} (${self.price_monthly}/mo)"

    def save(self, *args, **kwargs):
        # Ensure only one default plan
        if self.is_default:
            BillingPlan.objects.filter(is_default=True).update(is_default=False)
        super().save(*args, **kwargs)


class Subscription(models.Model):
    """User subscription to a billing plan."""

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        PAST_DUE = 'past_due', 'Past Due'
        CANCELLED = 'cancelled', 'Cancelled'
        TRIALING = 'trialing', 'Trialing'

    class Interval(models.TextChoices):
        MONTHLY = 'monthly', 'Monthly'
        YEARLY = 'yearly', 'Yearly'

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='subscription'
    )
    plan = models.ForeignKey(
        BillingPlan,
        on_delete=models.PROTECT,
        related_name='subscriptions'
    )

    # Billing interval
    interval = models.CharField(
        max_length=20,
        choices=Interval.choices,
        default=Interval.MONTHLY
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE
    )

    # Stripe
    stripe_subscription_id = models.CharField(max_length=100, blank=True)
    stripe_customer_id = models.CharField(max_length=100, blank=True)

    # Billing period
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    cancel_at_period_end = models.BooleanField(default=False)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Subscription'
        verbose_name_plural = 'Subscriptions'

    def __str__(self):
        return f"{self.user.email} - {self.plan.name}"

    @property
    def is_active(self):
        return self.status in [self.Status.ACTIVE, self.Status.TRIALING]


class UsageLog(models.Model):
    """Daily usage tracking for workspaces."""
    workspace = models.ForeignKey(
        'workspaces.Workspace',
        on_delete=models.CASCADE,
        related_name='usage_logs'
    )
    date = models.DateField()

    # Message counts
    message_count = models.IntegerField(default=0)
    token_count_input = models.IntegerField(default=0)
    token_count_output = models.IntegerField(default=0)

    # Cost tracking
    estimated_cost = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=Decimal('0.0000')
    )

    # Model breakdown
    model_usage = models.JSONField(
        default=dict,
        help_text='Usage breakdown by model'
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date']
        unique_together = ['workspace', 'date']
        verbose_name = 'Usage Log'
        verbose_name_plural = 'Usage Logs'

    def __str__(self):
        return f"{self.workspace.name} - {self.date}"

    @property
    def total_tokens(self):
        return self.token_count_input + self.token_count_output


class Invoice(models.Model):
    """Invoice records from Stripe."""

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        OPEN = 'open', 'Open'
        PAID = 'paid', 'Paid'
        VOID = 'void', 'Void'
        UNCOLLECTIBLE = 'uncollectible', 'Uncollectible'

    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
        related_name='invoices'
    )

    # Stripe
    stripe_invoice_id = models.CharField(max_length=100, unique=True)

    # Amount
    amount_due = models.DecimalField(max_digits=10, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    currency = models.CharField(max_length=3, default='usd')

    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )

    # URLs
    hosted_invoice_url = models.URLField(blank=True)
    invoice_pdf = models.URLField(blank=True)

    # Period
    period_start = models.DateTimeField(null=True)
    period_end = models.DateTimeField(null=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Invoice'
        verbose_name_plural = 'Invoices'

    def __str__(self):
        return f"Invoice {self.stripe_invoice_id} - {self.subscription.user.email}"
