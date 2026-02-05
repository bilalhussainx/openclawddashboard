"""
Billing views - Subscription and usage API endpoints.
"""
import stripe
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.utils import timezone
from django.db.models import Sum
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from .models import BillingPlan, Subscription, UsageLog, Invoice
from .serializers import (
    BillingPlanSerializer,
    SubscriptionSerializer,
    UsageLogSerializer,
    InvoiceSerializer,
    CreateCheckoutSessionSerializer,
    UsageSummarySerializer,
)

# Initialize Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


class BillingPlanViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for browsing billing plans.

    list: GET /api/billing/plans/
    retrieve: GET /api/billing/plans/{id}/
    """
    queryset = BillingPlan.objects.filter(is_active=True)
    serializer_class = BillingPlanSerializer
    permission_classes = [AllowAny]


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_subscription(request):
    """
    Get current user's subscription.

    GET /api/billing/subscription/
    """
    try:
        subscription = request.user.subscription
        serializer = SubscriptionSerializer(subscription)
        return Response(serializer.data)
    except Subscription.DoesNotExist:
        # Return free plan info if no subscription
        free_plan = BillingPlan.objects.filter(plan_type='free').first()
        return Response({
            'plan': BillingPlanSerializer(free_plan).data if free_plan else None,
            'status': 'free',
            'is_active': True,
        })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_checkout_session(request):
    """
    Create a Stripe checkout session for subscribing to a plan.

    POST /api/billing/checkout/
    """
    serializer = CreateCheckoutSessionSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    plan_id = serializer.validated_data['plan_id']
    interval = serializer.validated_data['interval']
    success_url = serializer.validated_data['success_url']
    cancel_url = serializer.validated_data['cancel_url']

    try:
        plan = BillingPlan.objects.get(id=plan_id, is_active=True)
    except BillingPlan.DoesNotExist:
        return Response(
            {'error': 'Plan not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    price_id = (
        plan.stripe_price_id_yearly
        if interval == 'yearly'
        else plan.stripe_price_id_monthly
    )

    if not price_id:
        return Response(
            {'error': 'Plan not available for this interval'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Get or create Stripe customer
    try:
        subscription = request.user.subscription
        customer_id = subscription.stripe_customer_id
    except Subscription.DoesNotExist:
        customer_id = None

    if not customer_id:
        customer = stripe.Customer.create(
            email=request.user.email,
            metadata={'user_id': request.user.id}
        )
        customer_id = customer.id

    # Create checkout session
    checkout_session = stripe.checkout.Session.create(
        customer=customer_id,
        payment_method_types=['card'],
        line_items=[{
            'price': price_id,
            'quantity': 1,
        }],
        mode='subscription',
        success_url=success_url + '?session_id={CHECKOUT_SESSION_ID}',
        cancel_url=cancel_url,
        metadata={
            'user_id': request.user.id,
            'plan_id': plan.id,
            'interval': interval,
        }
    )

    return Response({
        'checkout_url': checkout_session.url,
        'session_id': checkout_session.id,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_portal_session(request):
    """
    Create a Stripe billing portal session.

    POST /api/billing/portal/
    """
    return_url = request.data.get('return_url', settings.CORS_ALLOWED_ORIGINS[0])

    try:
        subscription = request.user.subscription
        if not subscription.stripe_customer_id:
            return Response(
                {'error': 'No billing account found'},
                status=status.HTTP_400_BAD_REQUEST
            )

        portal_session = stripe.billing_portal.Session.create(
            customer=subscription.stripe_customer_id,
            return_url=return_url,
        )

        return Response({'portal_url': portal_session.url})

    except Subscription.DoesNotExist:
        return Response(
            {'error': 'No subscription found'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_subscription(request):
    """
    Cancel the current subscription at period end.

    POST /api/billing/cancel/
    """
    try:
        subscription = request.user.subscription

        if not subscription.stripe_subscription_id:
            return Response(
                {'error': 'No active subscription'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Cancel at period end (not immediately)
        stripe.Subscription.modify(
            subscription.stripe_subscription_id,
            cancel_at_period_end=True
        )

        subscription.cancel_at_period_end = True
        subscription.save()

        return Response({
            'message': 'Subscription will cancel at the end of the billing period',
            'current_period_end': subscription.current_period_end,
        })

    except Subscription.DoesNotExist:
        return Response(
            {'error': 'No subscription found'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_usage_summary(request):
    """
    Get usage summary for current billing period.

    GET /api/billing/usage/
    """
    # Get date range (current month or billing period)
    end_date = timezone.now().date()
    start_date = end_date.replace(day=1)

    # Get user's workspaces
    workspace_ids = request.user.workspaces.values_list('id', flat=True)

    # Aggregate usage
    usage_logs = UsageLog.objects.filter(
        workspace_id__in=workspace_ids,
        date__gte=start_date,
        date__lte=end_date
    )

    totals = usage_logs.aggregate(
        total_messages=Sum('message_count'),
        total_tokens_in=Sum('token_count_input'),
        total_tokens_out=Sum('token_count_output'),
        total_cost=Sum('estimated_cost'),
    )

    return Response({
        'total_messages': totals['total_messages'] or 0,
        'total_tokens': (totals['total_tokens_in'] or 0) + (totals['total_tokens_out'] or 0),
        'total_cost': str(totals['total_cost'] or Decimal('0.00')),
        'period_start': start_date,
        'period_end': end_date,
        'daily_usage': UsageLogSerializer(usage_logs, many=True).data,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_invoices(request):
    """
    Get invoice history.

    GET /api/billing/invoices/
    """
    try:
        subscription = request.user.subscription
        invoices = subscription.invoices.all()[:20]
        serializer = InvoiceSerializer(invoices, many=True)
        return Response(serializer.data)
    except Subscription.DoesNotExist:
        return Response([])
