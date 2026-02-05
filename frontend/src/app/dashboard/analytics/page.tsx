'use client';

import { useQuery } from '@tanstack/react-query';
import { billingApi, workspaceApi } from '@/lib/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { BarChart3, MessageSquare, Zap, DollarSign, Loader2 } from 'lucide-react';
import { formatNumber, formatCurrency, formatDate } from '@/lib/utils';

export default function AnalyticsPage() {
  const { data: usage, isLoading: usageLoading } = useQuery({
    queryKey: ['usage'],
    queryFn: async () => {
      const response = await billingApi.usage();
      return response.data;
    },
  });

  const { data: workspaces } = useQuery({
    queryKey: ['workspaces'],
    queryFn: async () => {
      const response = await workspaceApi.list();
      return response.data.results || response.data;
    },
  });

  const runningCount = workspaces?.filter((w: any) => w.status === 'running').length || 0;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Analytics</h1>
        <p className="text-muted-foreground">Monitor your usage and track performance</p>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Messages This Month</CardTitle>
            <MessageSquare className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {usageLoading ? '...' : formatNumber(usage?.total_messages || 0)}
            </div>
            <p className="text-xs text-muted-foreground">
              {usage?.period_start && `Since ${formatDate(usage.period_start)}`}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Tokens</CardTitle>
            <Zap className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {usageLoading ? '...' : formatNumber(usage?.total_tokens || 0)}
            </div>
            <p className="text-xs text-muted-foreground">Input + Output tokens</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Estimated Cost</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {usageLoading ? '...' : formatCurrency(parseFloat(usage?.total_cost || '0'))}
            </div>
            <p className="text-xs text-muted-foreground">Based on token usage</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Workspaces</CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{runningCount}</div>
            <p className="text-xs text-muted-foreground">
              of {workspaces?.length || 0} total
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Daily Usage */}
      <Card>
        <CardHeader>
          <CardTitle>Daily Usage</CardTitle>
          <CardDescription>Message and token usage over time</CardDescription>
        </CardHeader>
        <CardContent>
          {usageLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : usage?.daily_usage && usage.daily_usage.length > 0 ? (
            <div className="space-y-4">
              {usage.daily_usage.map((day: any) => (
                <div key={day.id} className="flex items-center justify-between p-4 rounded-lg border">
                  <div>
                    <p className="font-medium">{formatDate(day.date)}</p>
                    <p className="text-sm text-muted-foreground">{day.workspace_name}</p>
                  </div>
                  <div className="flex items-center gap-6 text-sm">
                    <div className="text-right">
                      <p className="font-medium">{formatNumber(day.message_count)}</p>
                      <p className="text-muted-foreground">messages</p>
                    </div>
                    <div className="text-right">
                      <p className="font-medium">{formatNumber(day.total_tokens)}</p>
                      <p className="text-muted-foreground">tokens</p>
                    </div>
                    <div className="text-right">
                      <p className="font-medium">{formatCurrency(parseFloat(day.estimated_cost))}</p>
                      <p className="text-muted-foreground">cost</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <BarChart3 className="h-12 w-12 text-muted-foreground mb-4" />
              <h3 className="font-medium mb-1">No usage data yet</h3>
              <p className="text-sm text-muted-foreground">
                Start using your assistant to see analytics
              </p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
