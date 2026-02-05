'use client';

import { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { workspaceApi, channelApi, agentTaskApi } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useToast } from '@/components/ui/use-toast';
import {
  ArrowLeft,
  Play,
  Square,
  RefreshCw,
  Settings,
  Trash2,
  MessageSquare,
  Plus,
  Loader2,
  Terminal,
  Bot,
  ListTodo,
  Puzzle,
  Briefcase,
  TrendingUp,
  ExternalLink,
  Star,
  Eye,
  Clock,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Workspace } from '@/stores/workspace';

export default function WorkspaceDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const workspaceId = Number(params.id);

  const [showTelegramSetup, setShowTelegramSetup] = useState(false);
  const [telegramToken, setTelegramToken] = useState('');
  const [showLogs, setShowLogs] = useState(false);

  const { data: workspace, isLoading } = useQuery<Workspace>({
    queryKey: ['workspace', workspaceId],
    queryFn: async () => {
      const response = await workspaceApi.get(workspaceId);
      return response.data;
    },
  });

  const { data: logs } = useQuery({
    queryKey: ['workspace-logs', workspaceId],
    queryFn: async () => {
      const response = await workspaceApi.logs(workspaceId, 50);
      return response.data;
    },
    enabled: showLogs && workspace?.status === 'running',
    refetchInterval: showLogs ? 5000 : false,
  });

  // Fetch tasks with recent results
  const { data: tasksData } = useQuery({
    queryKey: ['tasks', workspaceId],
    queryFn: async () => {
      const response = await agentTaskApi.list(workspaceId);
      return response.data.results || response.data;
    },
  });

  // Get all recent results from all tasks
  const recentResults = tasksData
    ?.flatMap((task: any) =>
      (task.recent_results || []).map((r: any) => ({ ...r, taskName: task.name, taskId: task.id }))
    )
    .slice(0, 5) || [];

  const deployMutation = useMutation({
    mutationFn: () => workspaceApi.deploy(workspaceId),
    onSuccess: () => {
      toast({ title: 'Deployment started' });
      queryClient.invalidateQueries({ queryKey: ['workspace', workspaceId] });
    },
    onError: (error: any) => {
      toast({
        variant: 'destructive',
        title: 'Deployment failed',
        description: error.response?.data?.error || 'Something went wrong',
      });
    },
  });

  const stopMutation = useMutation({
    mutationFn: () => workspaceApi.stop(workspaceId),
    onSuccess: () => {
      toast({ title: 'Stop command sent' });
      queryClient.invalidateQueries({ queryKey: ['workspace', workspaceId] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => workspaceApi.delete(workspaceId),
    onSuccess: () => {
      toast({ title: 'Workspace deleted' });
      router.push('/dashboard');
    },
  });

  const addTelegramMutation = useMutation({
    mutationFn: (token: string) => channelApi.setupTelegram(workspaceId, token),
    onSuccess: () => {
      toast({ title: 'Telegram channel added' });
      setShowTelegramSetup(false);
      setTelegramToken('');
      queryClient.invalidateQueries({ queryKey: ['workspace', workspaceId] });
    },
    onError: (error: any) => {
      toast({
        variant: 'destructive',
        title: 'Failed to add channel',
        description: error.response?.data?.error || 'Something went wrong',
      });
    },
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!workspace) {
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground">Workspace not found</p>
      </div>
    );
  }

  const statusColor = {
    pending: 'secondary',
    deploying: 'warning',
    running: 'success',
    stopped: 'secondary',
    error: 'destructive',
  }[workspace.status] as any;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <Link
            href="/dashboard"
            className="flex items-center text-sm text-muted-foreground hover:text-foreground mb-2"
          >
            <ArrowLeft className="h-4 w-4 mr-1" />
            Back to Dashboard
          </Link>
          <h1 className="text-2xl font-bold">{workspace.name}</h1>
          <p className="text-muted-foreground">{workspace.description || 'No description'}</p>
        </div>
        <div className="flex items-center space-x-2">
          <Badge variant={statusColor}>{workspace.status_display}</Badge>
          {workspace.status === 'running' ? (
            <Button
              variant="outline"
              size="sm"
              onClick={() => stopMutation.mutate()}
              disabled={stopMutation.isPending}
            >
              <Square className="h-4 w-4 mr-2" />
              Stop
            </Button>
          ) : (
            <Button
              size="sm"
              onClick={() => deployMutation.mutate()}
              disabled={deployMutation.isPending || workspace.status === 'deploying'}
            >
              {deployMutation.isPending ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Play className="h-4 w-4 mr-2" />
              )}
              Deploy
            </Button>
          )}
        </div>
      </div>

      {/* Error Message */}
      {workspace.error_message && (
        <Card className="border-destructive bg-destructive/5">
          <CardContent className="p-4">
            <p className="text-sm text-destructive">{workspace.error_message}</p>
          </CardContent>
        </Card>
      )}

      {/* Agent Configuration - Primary Actions */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <Card className="border-primary/50 bg-primary/5">
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="h-12 w-12 rounded-lg bg-primary/10 flex items-center justify-center">
                <Bot className="h-6 w-6 text-primary" />
              </div>
              <div className="flex-1">
                <h3 className="text-lg font-semibold">Configure Agent</h3>
                <p className="text-sm text-muted-foreground">
                  System prompt, knowledge base, behavior
                </p>
              </div>
              <Link href={`/dashboard/workspaces/${workspaceId}/agent`}>
                <Button>
                  <Settings className="h-4 w-4 mr-2" />
                  Configure
                </Button>
              </Link>
            </div>
          </CardContent>
        </Card>

        <Card className="border-blue-500/50 bg-blue-500/5">
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="h-12 w-12 rounded-lg bg-blue-500/10 flex items-center justify-center">
                <ListTodo className="h-6 w-6 text-blue-500" />
              </div>
              <div className="flex-1">
                <h3 className="text-lg font-semibold">Agent Tasks</h3>
                <p className="text-sm text-muted-foreground">
                  {tasksData && tasksData.length > 0
                    ? `${tasksData.length} task${tasksData.length > 1 ? 's' : ''} configured`
                    : 'Automated jobs, web scraping, monitoring'}
                </p>
              </div>
              <div className="flex gap-2">
                {tasksData && tasksData.length > 0 && tasksData[0].result_count > 0 && (
                  <Link href={`/dashboard/workspaces/${workspaceId}/tasks/${tasksData[0].id}`}>
                    <Button size="sm">
                      <Eye className="h-4 w-4 mr-2" />
                      Results
                      <Badge variant="secondary" className="ml-2">
                        {tasksData[0].result_count}
                      </Badge>
                    </Button>
                  </Link>
                )}
                <Link href={`/dashboard/workspaces/${workspaceId}/tasks`}>
                  <Button variant="outline">
                    <ListTodo className="h-4 w-4 mr-2" />
                    Manage
                  </Button>
                </Link>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-purple-500/50 bg-purple-500/5">
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="h-12 w-12 rounded-lg bg-purple-500/10 flex items-center justify-center">
                <Puzzle className="h-6 w-6 text-purple-500" />
              </div>
              <div className="flex-1">
                <h3 className="text-lg font-semibold">Installed Skills</h3>
                <p className="text-sm text-muted-foreground">
                  Extend capabilities with skills
                </p>
              </div>
              <Link href={`/dashboard/workspaces/${workspaceId}/skills`}>
                <Button variant="outline">
                  <Puzzle className="h-4 w-4 mr-2" />
                  Skills
                </Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Info Cards */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Model</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-lg font-semibold">{workspace.model_display}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Port</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-lg font-semibold">{workspace.assigned_port || 'Not assigned'}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Sandbox Mode</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-lg font-semibold">{workspace.sandbox_mode ? 'Enabled' : 'Disabled'}</p>
          </CardContent>
        </Card>
      </div>

      {/* Recent Job Results */}
      {recentResults.length > 0 && (
        <Card className="border-green-500/50 bg-green-500/5">
          <CardHeader className="flex flex-row items-center justify-between pb-3">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Briefcase className="h-5 w-5 text-green-600" />
                Recent Job Results
              </CardTitle>
              <CardDescription>Latest jobs found by your agent tasks</CardDescription>
            </div>
            <Link href={`/dashboard/workspaces/${workspaceId}/tasks`}>
              <Button size="sm" variant="outline">
                <Eye className="h-4 w-4 mr-2" />
                View All Tasks
              </Button>
            </Link>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {recentResults.map((result: any, idx: number) => (
                <div
                  key={`${result.taskId}-${result.id}-${idx}`}
                  className="flex items-center justify-between p-4 rounded-lg border bg-background hover:border-primary/50 transition-colors"
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <h4 className="font-medium truncate">{result.title}</h4>
                      {result.score !== null && result.score !== undefined && (
                        <Badge
                          className={
                            result.score >= 70
                              ? "bg-green-500 hover:bg-green-600"
                              : result.score >= 40
                                ? "bg-yellow-500 hover:bg-yellow-600"
                                : ""
                          }
                          variant={result.score < 40 ? "secondary" : undefined}
                        >
                          <Star className="h-3 w-3 mr-1" />
                          {result.score}
                        </Badge>
                      )}
                    </div>
                    <div className="flex items-center gap-3 text-sm text-muted-foreground">
                      {result.data?.company && (
                        <span>{result.data.company}</span>
                      )}
                      {result.data?.location && (
                        <span>{result.data.location}</span>
                      )}
                      {result.data?.salary && (
                        <span className="text-green-600">{result.data.salary}</span>
                      )}
                    </div>
                    <div className="flex items-center gap-2 mt-1">
                      <Badge variant="outline" className="text-xs">
                        {result.taskName}
                      </Badge>
                      {result.found_at && (
                        <span className="text-xs text-muted-foreground flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {new Date(result.found_at).toLocaleDateString()}
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 ml-4">
                    {result.url && (
                      <a
                        href={result.url}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        <Button size="sm">
                          <ExternalLink className="h-4 w-4 mr-1" />
                          Apply
                        </Button>
                      </a>
                    )}
                    <Link href={`/dashboard/workspaces/${workspaceId}/tasks/${result.taskId}`}>
                      <Button size="sm" variant="outline">
                        <Eye className="h-4 w-4" />
                      </Button>
                    </Link>
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-4 text-center">
              <Link href={`/dashboard/workspaces/${workspaceId}/tasks`}>
                <Button variant="ghost" className="text-primary">
                  <TrendingUp className="h-4 w-4 mr-2" />
                  View All Results & Run New Tasks
                </Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Channels */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Connected Channels</CardTitle>
            <CardDescription>Messaging platforms connected to this workspace</CardDescription>
          </div>
          <Button size="sm" variant="outline" onClick={() => setShowTelegramSetup(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Add Channel
          </Button>
        </CardHeader>
        <CardContent>
          {workspace.channels.length === 0 ? (
            <div className="text-center py-8">
              <MessageSquare className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <p className="text-muted-foreground">No channels connected yet</p>
              <Button
                variant="outline"
                className="mt-4"
                onClick={() => setShowTelegramSetup(true)}
              >
                Connect Telegram
              </Button>
            </div>
          ) : (
            <div className="space-y-3">
              {workspace.channels.map((channel) => (
                <div
                  key={channel.id}
                  className="flex items-center justify-between p-4 rounded-lg border"
                >
                  <div className="flex items-center space-x-3">
                    <div className={cn(
                      'h-10 w-10 rounded-lg flex items-center justify-center',
                      channel.channel_type === 'telegram' ? 'bg-blue-500' : 'bg-purple-500'
                    )}>
                      <MessageSquare className="h-5 w-5 text-white" />
                    </div>
                    <div>
                      <p className="font-medium">{channel.channel_type_display}</p>
                      <p className="text-sm text-muted-foreground">
                        {channel.is_active ? 'Active' : 'Inactive'}
                      </p>
                    </div>
                  </div>
                  <Badge variant={channel.is_active ? 'success' : 'secondary'}>
                    {channel.is_active ? 'Connected' : 'Disconnected'}
                  </Badge>
                </div>
              ))}
            </div>
          )}

          {/* Telegram Setup Form */}
          {showTelegramSetup && (
            <div className="mt-4 p-4 border rounded-lg space-y-4">
              <h4 className="font-medium">Add Telegram Channel</h4>
              <div className="space-y-2">
                <Label htmlFor="telegramToken">Bot Token</Label>
                <Input
                  id="telegramToken"
                  placeholder="123456:ABC-DEF..."
                  value={telegramToken}
                  onChange={(e) => setTelegramToken(e.target.value)}
                />
                <p className="text-xs text-muted-foreground">
                  Get this from @BotFather on Telegram
                </p>
              </div>
              <div className="flex space-x-2">
                <Button
                  size="sm"
                  onClick={() => addTelegramMutation.mutate(telegramToken)}
                  disabled={!telegramToken || addTelegramMutation.isPending}
                >
                  {addTelegramMutation.isPending && (
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  )}
                  Add Channel
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    setShowTelegramSetup(false);
                    setTelegramToken('');
                  }}
                >
                  Cancel
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Logs */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Container Logs</CardTitle>
            <CardDescription>View logs from your OpenClaw instance</CardDescription>
          </div>
          <Button
            size="sm"
            variant="outline"
            onClick={() => setShowLogs(!showLogs)}
          >
            <Terminal className="h-4 w-4 mr-2" />
            {showLogs ? 'Hide Logs' : 'Show Logs'}
          </Button>
        </CardHeader>
        {showLogs && (
          <CardContent>
            {workspace.status !== 'running' ? (
              <p className="text-muted-foreground text-sm">
                Deploy the workspace to view logs
              </p>
            ) : (
              <pre className="bg-muted p-4 rounded-lg text-xs overflow-auto max-h-64">
                {logs?.logs || 'Loading logs...'}
              </pre>
            )}
          </CardContent>
        )}
      </Card>

      {/* Danger Zone */}
      <Card className="border-destructive/50">
        <CardHeader>
          <CardTitle className="text-destructive">Danger Zone</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium">Delete Workspace</p>
              <p className="text-sm text-muted-foreground">
                Permanently delete this workspace and all its data
              </p>
            </div>
            <Button
              variant="destructive"
              size="sm"
              onClick={() => {
                if (confirm('Are you sure you want to delete this workspace?')) {
                  deleteMutation.mutate();
                }
              }}
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending && (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              )}
              <Trash2 className="h-4 w-4 mr-2" />
              Delete
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
