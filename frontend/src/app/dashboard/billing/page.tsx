'use client';

import { useQuery } from '@tanstack/react-query';
import { billingApi } from '@/lib/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Check, CreditCard, FileText, Loader2 } from 'lucide-react';
import { formatCurrency, formatDate } from '@/lib/utils';

interface BillingPlan {
  id: number;
  name: string;
  plan_type: string;
  description: string;
  price_monthly: string;
  price_yearly: string;
  max_workspaces: number;
  max_channels: number;
  max_messages_per_month: number;
  max_skills: number;
  features: string[];
  is_active: boolean;
}

export default function BillingPage() {
  const { data: subscription, isLoading: subLoading } = useQuery({
    queryKey: ['subscription'],
    queryFn: async () => {
      const response = await billingApi.subscription();
      return response.data;
    },
  });

  const { data: plans, isLoading: plansLoading } = useQuery<BillingPlan[]>({
    queryKey: ['billing-plans'],
    queryFn: async () => {
      const response = await billingApi.plans();
      return response.data.results || response.data;
    },
  });

  const { data: invoices } = useQuery({
    queryKey: ['invoices'],
    queryFn: async () => {
      const response = await billingApi.invoices();
      return response.data;
    },
  });

  const currentPlan = subscription?.plan;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Billing</h1>
        <p className="text-muted-foreground">Manage your subscription and billing</p>
      </div>

      {/* Current Plan */}
      <Card>
        <CardHeader>
          <CardTitle>Current Plan</CardTitle>
          <CardDescription>Your active subscription</CardDescription>
        </CardHeader>
        <CardContent>
          {subLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : (
            <div className="flex items-center justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-xl font-bold">{currentPlan?.name || 'Free'}</h3>
                  <Badge variant={subscription?.is_active ? 'success' : 'secondary'}>
                    {subscription?.status || 'Active'}
                  </Badge>
                </div>
                <p className="text-muted-foreground">
                  {currentPlan?.description || 'Basic features for getting started'}
                </p>
                {subscription?.current_period_end && (
                  <p className="text-sm text-muted-foreground mt-2">
                    {subscription.cancel_at_period_end
                      ? `Cancels on ${formatDate(subscription.current_period_end)}`
                      : `Renews on ${formatDate(subscription.current_period_end)}`}
                  </p>
                )}
              </div>
              <div className="text-right">
                <p className="text-3xl font-bold">
                  {formatCurrency(parseFloat(currentPlan?.price_monthly || '0'))}
                </p>
                <p className="text-sm text-muted-foreground">per month</p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Available Plans */}
      <div>
        <h2 className="text-lg font-semibold mb-4">Available Plans</h2>
        {plansLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-3">
            {plans?.map((plan) => (
              <Card
                key={plan.id}
                className={plan.plan_type === 'pro' ? 'border-primary' : ''}
              >
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle>{plan.name}</CardTitle>
                    {plan.plan_type === 'pro' && (
                      <Badge>Popular</Badge>
                    )}
                  </div>
                  <div className="mt-2">
                    <span className="text-3xl font-bold">
                      {formatCurrency(parseFloat(plan.price_monthly))}
                    </span>
                    <span className="text-muted-foreground">/month</span>
                  </div>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-2">
                    {plan.features?.map((feature, i) => (
                      <li key={i} className="flex items-center gap-2 text-sm">
                        <Check className="h-4 w-4 text-green-500" />
                        {feature}
                      </li>
                    ))}
                  </ul>
                  <Button
                    className="w-full mt-4"
                    variant={currentPlan?.id === plan.id ? 'outline' : 'default'}
                    disabled={currentPlan?.id === plan.id}
                  >
                    {currentPlan?.id === plan.id ? 'Current Plan' : 'Upgrade'}
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* Invoices */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Invoice History
          </CardTitle>
        </CardHeader>
        <CardContent>
          {invoices && invoices.length > 0 ? (
            <div className="space-y-4">
              {invoices.map((invoice: any) => (
                <div
                  key={invoice.id}
                  className="flex items-center justify-between p-4 rounded-lg border"
                >
                  <div>
                    <p className="font-medium">{formatDate(invoice.created_at)}</p>
                    <p className="text-sm text-muted-foreground">
                      {invoice.stripe_invoice_id}
                    </p>
                  </div>
                  <div className="flex items-center gap-4">
                    <Badge variant={invoice.status === 'paid' ? 'success' : 'secondary'}>
                      {invoice.status}
                    </Badge>
                    <span className="font-medium">
                      {formatCurrency(parseFloat(invoice.amount_due))}
                    </span>
                    {invoice.hosted_invoice_url && (
                      <Button size="sm" variant="outline" asChild>
                        <a href={invoice.hosted_invoice_url} target="_blank" rel="noopener noreferrer">
                          View
                        </a>
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-8 text-center">
              <CreditCard className="h-12 w-12 text-muted-foreground mb-4" />
              <h3 className="font-medium mb-1">No invoices yet</h3>
              <p className="text-sm text-muted-foreground">
                Your invoice history will appear here
              </p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
