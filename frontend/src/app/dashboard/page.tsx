'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { workspaceApi, billingApi } from '@/lib/api';
import { useWorkspaceStore, Workspace } from '@/stores/workspace';
import { useAuthStore } from '@/stores/auth';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Box,
  MessageSquare,
  Zap,
  ArrowRight,
  Plus,
  AlertCircle,
  CheckCircle2,
  Loader2,
} from 'lucide-react';
import { formatNumber } from '@/lib/utils';

export default function DashboardPage() {
  const { user } = useAuthStore();
  const { setWorkspaces } = useWorkspaceStore();

  const { data: workspacesData, isLoading: workspacesLoading } = useQuery({
    queryKey: ['workspaces'],
    queryFn: async () => {
      const response = await workspaceApi.list();
      return response.data.results || response.data;
    },
  });

  const { data: usageData } = useQuery({
    queryKey: ['usage'],
    queryFn: async () => {
      const response = await billingApi.usage();
      return response.data;
    },
  });

  useEffect(() => {
    if (workspacesData) {
      setWorkspaces(workspacesData);
    }
  }, [workspacesData, setWorkspaces]);

  const workspaces: Workspace[] = workspacesData || [];
  const runningWorkspaces = workspaces.filter((w) => w.status === 'running');
  const totalChannels = workspaces.reduce((acc, w) => acc + w.channels.length, 0);

  const needsSetup = !user?.has_anthropic_key && !user?.has_openai_key;

  return (
    <div className="space-y-6">
      {/* Welcome & Setup Alert */}
      {needsSetup && (
        <Card className="border-yellow-500/50 bg-yellow-500/5">
          <CardContent className="flex items-center justify-between p-4">
            <div className="flex items-center space-x-3">
              <AlertCircle className="h-5 w-5 text-yellow-500" />
              <div>
                <p className="font-medium">Complete your setup</p>
                <p className="text-sm text-muted-foreground">
                  Add your API key to start deploying AI assistants
                </p>
              </div>
            </div>
            <Link href="/dashboard/settings">
              <Button variant="outline" size="sm">
                Add API Key
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </Link>
          </CardContent>
        </Card>
      )}

      {/* Stats Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Workspaces</CardTitle>
            <Box className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{workspaces.length}</div>
            <p className="text-xs text-muted-foreground">
              {runningWorkspaces.length} running
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Connected Channels</CardTitle>
            <MessageSquare className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalChannels}</div>
            <p className="text-xs text-muted-foreground">Across all workspaces</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Messages This Month</CardTitle>
            <Zap className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatNumber(usageData?.total_messages || 0)}
            </div>
            <p className="text-xs text-muted-foreground">
              {formatNumber(usageData?.total_tokens || 0)} tokens
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">API Status</CardTitle>
            {user?.has_anthropic_key || user?.has_openai_key ? (
              <CheckCircle2 className="h-4 w-4 text-green-500" />
            ) : (
              <AlertCircle className="h-4 w-4 text-yellow-500" />
            )}
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {user?.has_anthropic_key || user?.has_openai_key ? 'Connected' : 'Not Set'}
            </div>
            <p className="text-xs text-muted-foreground">
              {user?.has_anthropic_key && 'Anthropic'}
              {user?.has_anthropic_key && user?.has_openai_key && ' & '}
              {user?.has_openai_key && 'OpenAI'}
              {!user?.has_anthropic_key && !user?.has_openai_key && 'Add API key to deploy'}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Workspaces List */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Your Workspaces</CardTitle>
            <CardDescription>Manage your AI assistant deployments</CardDescription>
          </div>
          <Link href="/dashboard/workspaces/new">
            <Button size="sm">
              <Plus className="h-4 w-4 mr-2" />
              New Workspace
            </Button>
          </Link>
        </CardHeader>
        <CardContent>
          {workspacesLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : workspaces.length === 0 ? (
            <div className="text-center py-8">
              <Box className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <h3 className="font-medium mb-1">No workspaces yet</h3>
              <p className="text-sm text-muted-foreground mb-4">
                Create your first workspace to deploy an AI assistant
              </p>
              <Link href="/dashboard/workspaces/new">
                <Button>
                  <Plus className="h-4 w-4 mr-2" />
                  Create Workspace
                </Button>
              </Link>
            </div>
          ) : (
            <div className="space-y-4">
              {workspaces.map((workspace) => (
                <Link
                  key={workspace.id}
                  href={`/dashboard/workspaces/${workspace.id}`}
                  className="block"
                >
                  <div className="flex items-center justify-between p-4 rounded-lg border hover:bg-muted/50 transition-colors">
                    <div className="flex items-center space-x-4">
                      <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
                        <Box className="h-5 w-5 text-primary" />
                      </div>
                      <div>
                        <h4 className="font-medium">{workspace.name}</h4>
                        <p className="text-sm text-muted-foreground">
                          {workspace.channels.length} channels · {workspace.model_display}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center space-x-3">
                      <Badge
                        variant={
                          workspace.status === 'running'
                            ? 'success'
                            : workspace.status === 'error'
                            ? 'destructive'
                            : 'secondary'
                        }
                      >
                        {workspace.status_display}
                      </Badge>
                      <ArrowRight className="h-4 w-4 text-muted-foreground" />
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Quick Actions */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Quick Start Guide</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center space-x-3">
              <div className={`h-6 w-6 rounded-full flex items-center justify-center text-xs font-medium ${
                user?.has_anthropic_key || user?.has_openai_key
                  ? 'bg-green-500 text-white'
                  : 'bg-muted text-muted-foreground'
              }`}>
                {user?.has_anthropic_key || user?.has_openai_key ? '✓' : '1'}
              </div>
              <span className={user?.has_anthropic_key || user?.has_openai_key ? 'line-through text-muted-foreground' : ''}>
                Add your API key (Anthropic or OpenAI)
              </span>
            </div>
            <div className="flex items-center space-x-3">
              <div className={`h-6 w-6 rounded-full flex items-center justify-center text-xs font-medium ${
                workspaces.length > 0
                  ? 'bg-green-500 text-white'
                  : 'bg-muted text-muted-foreground'
              }`}>
                {workspaces.length > 0 ? '✓' : '2'}
              </div>
              <span className={workspaces.length > 0 ? 'line-through text-muted-foreground' : ''}>
                Create a workspace
              </span>
            </div>
            <div className="flex items-center space-x-3">
              <div className={`h-6 w-6 rounded-full flex items-center justify-center text-xs font-medium ${
                totalChannels > 0
                  ? 'bg-green-500 text-white'
                  : 'bg-muted text-muted-foreground'
              }`}>
                {totalChannels > 0 ? '✓' : '3'}
              </div>
              <span className={totalChannels > 0 ? 'line-through text-muted-foreground' : ''}>
                Connect a messaging channel
              </span>
            </div>
            <div className="flex items-center space-x-3">
              <div className={`h-6 w-6 rounded-full flex items-center justify-center text-xs font-medium ${
                runningWorkspaces.length > 0
                  ? 'bg-green-500 text-white'
                  : 'bg-muted text-muted-foreground'
              }`}>
                {runningWorkspaces.length > 0 ? '✓' : '4'}
              </div>
              <span className={runningWorkspaces.length > 0 ? 'line-through text-muted-foreground' : ''}>
                Deploy your assistant
              </span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Resources</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <a
              href="https://docs.openclaw.ai"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-between p-3 rounded-lg border hover:bg-muted/50 transition-colors"
            >
              <span>Documentation</span>
              <ArrowRight className="h-4 w-4" />
            </a>
            <a
              href="https://github.com/openclaw/openclaw"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-between p-3 rounded-lg border hover:bg-muted/50 transition-colors"
            >
              <span>GitHub Repository</span>
              <ArrowRight className="h-4 w-4" />
            </a>
            <a
              href="https://discord.gg/openclaw"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-between p-3 rounded-lg border hover:bg-muted/50 transition-colors"
            >
              <span>Discord Community</span>
              <ArrowRight className="h-4 w-4" />
            </a>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
