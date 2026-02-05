"""
Stripe webhook handlers.
"""
import stripe
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import BillingPlan, Subscription, Invoice

User = get_user_model()
stripe.api_key = settings.STRIPE_SECRET_KEY


@csrf_exempt
@require_POST
def stripe_webhook(request):
    """
    Handle Stripe webhooks.

    POST /api/billing/webhook/
    """
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status=400)

    # Handle the event
    event_type = event['type']
    data = event['data']['object']

    if event_type == 'checkout.session.completed':
        handle_checkout_completed(data)

    elif event_type == 'customer.subscription.created':
        handle_subscription_created(data)

    elif event_type == 'customer.subscription.updated':
        handle_subscription_updated(data)

    elif event_type == 'customer.subscription.deleted':
        handle_subscription_deleted(data)

    elif event_type == 'invoice.paid':
        handle_invoice_paid(data)

    elif event_type == 'invoice.payment_failed':
        handle_invoice_payment_failed(data)

    return HttpResponse(status=200)


def handle_checkout_completed(session):
    """Handle successful checkout session."""
    user_id = session['metadata'].get('user_id')
    plan_id = session['metadata'].get('plan_id')
    interval = session['metadata'].get('interval', 'monthly')

    if not user_id or not plan_id:
        return

    try:
        user = User.objects.get(id=user_id)
        plan = BillingPlan.objects.get(id=plan_id)
    except (User.DoesNotExist, BillingPlan.DoesNotExist):
        return

    # Get subscription from Stripe
    stripe_subscription = stripe.Subscription.retrieve(session['subscription'])

    # Create or update subscription
    subscription, created = Subscription.objects.update_or_create(
        user=user,
        defaults={
            'plan': plan,
            'interval': interval,
            'status': Subscription.Status.ACTIVE,
            'stripe_subscription_id': stripe_subscription.id,
            'stripe_customer_id': session['customer'],
            'current_period_start': timezone.datetime.fromtimestamp(
                stripe_subscription['current_period_start'],
                tz=timezone.utc
            ),
            'current_period_end': timezone.datetime.fromtimestamp(
                stripe_subscription['current_period_end'],
                tz=timezone.utc
            ),
        }
    )


def handle_subscription_created(stripe_subscription):
    """Handle new subscription created."""
    customer_id = stripe_subscription['customer']

    try:
        subscription = Subscription.objects.get(stripe_customer_id=customer_id)
        subscription.stripe_subscription_id = stripe_subscription['id']
        subscription.status = map_stripe_status(stripe_subscription['status'])
        subscription.current_period_start = timezone.datetime.fromtimestamp(
            stripe_subscription['current_period_start'],
            tz=timezone.utc
        )
        subscription.current_period_end = timezone.datetime.fromtimestamp(
            stripe_subscription['current_period_end'],
            tz=timezone.utc
        )
        subscription.save()
    except Subscription.DoesNotExist:
        pass


def handle_subscription_updated(stripe_subscription):
    """Handle subscription updates (plan changes, status changes)."""
    try:
        subscription = Subscription.objects.get(
            stripe_subscription_id=stripe_subscription['id']
        )

        subscription.status = map_stripe_status(stripe_subscription['status'])
        subscription.cancel_at_period_end = stripe_subscription.get('cancel_at_period_end', False)
        subscription.current_period_start = timezone.datetime.fromtimestamp(
            stripe_subscription['current_period_start'],
            tz=timezone.utc
        )
        subscription.current_period_end = timezone.datetime.fromtimestamp(
            stripe_subscription['current_period_end'],
            tz=timezone.utc
        )
        subscription.save()

    except Subscription.DoesNotExist:
        pass


def handle_subscription_deleted(stripe_subscription):
    """Handle subscription cancellation."""
    try:
        subscription = Subscription.objects.get(
            stripe_subscription_id=stripe_subscription['id']
        )
        subscription.status = Subscription.Status.CANCELLED
        subscription.save()

        # Optionally: downgrade to free plan
        free_plan = BillingPlan.objects.filter(plan_type='free').first()
        if free_plan:
            subscription.plan = free_plan
            subscription.stripe_subscription_id = ''
            subscription.save()

    except Subscription.DoesNotExist:
        pass


def handle_invoice_paid(stripe_invoice):
    """Handle successful invoice payment."""
    try:
        subscription = Subscription.objects.get(
            stripe_subscription_id=stripe_invoice.get('subscription')
        )

        Invoice.objects.update_or_create(
            stripe_invoice_id=stripe_invoice['id'],
            defaults={
                'subscription': subscription,
                'amount_due': stripe_invoice['amount_due'] / 100,
                'amount_paid': stripe_invoice['amount_paid'] / 100,
                'currency': stripe_invoice['currency'],
                'status': Invoice.Status.PAID,
                'hosted_invoice_url': stripe_invoice.get('hosted_invoice_url', ''),
                'invoice_pdf': stripe_invoice.get('invoice_pdf', ''),
                'period_start': timezone.datetime.fromtimestamp(
                    stripe_invoice['period_start'],
                    tz=timezone.utc
                ) if stripe_invoice.get('period_start') else None,
                'period_end': timezone.datetime.fromtimestamp(
                    stripe_invoice['period_end'],
                    tz=timezone.utc
                ) if stripe_invoice.get('period_end') else None,
                'paid_at': timezone.now(),
            }
        )

        # Update subscription status
        subscription.status = Subscription.Status.ACTIVE
        subscription.save()

    except Subscription.DoesNotExist:
        pass


def handle_invoice_payment_failed(stripe_invoice):
    """Handle failed invoice payment."""
    try:
        subscription = Subscription.objects.get(
            stripe_subscription_id=stripe_invoice.get('subscription')
        )

        subscription.status = Subscription.Status.PAST_DUE
        subscription.save()

        Invoice.objects.update_or_create(
            stripe_invoice_id=stripe_invoice['id'],
            defaults={
                'subscription': subscription,
                'amount_due': stripe_invoice['amount_due'] / 100,
                'currency': stripe_invoice['currency'],
                'status': Invoice.Status.OPEN,
                'hosted_invoice_url': stripe_invoice.get('hosted_invoice_url', ''),
            }
        )

    except Subscription.DoesNotExist:
        pass


def map_stripe_status(stripe_status):
    """Map Stripe subscription status to our status."""
    status_map = {
        'active': Subscription.Status.ACTIVE,
        'past_due': Subscription.Status.PAST_DUE,
        'canceled': Subscription.Status.CANCELLED,
        'trialing': Subscription.Status.TRIALING,
        'unpaid': Subscription.Status.PAST_DUE,
    }
    return status_map.get(stripe_status, Subscription.Status.ACTIVE)
