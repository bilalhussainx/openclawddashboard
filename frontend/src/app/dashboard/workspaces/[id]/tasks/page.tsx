'use client';

import { useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { workspaceApi, agentTaskApi } from '@/lib/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { useToast } from '@/components/ui/use-toast';
import {
  ArrowLeft,
  Play,
  Pause,
  Plus,
  Trash2,
  Loader2,
  Clock,
  CheckCircle,
  XCircle,
  ListTodo,
  Zap,
  ExternalLink,
  RefreshCw,
  Eye,
  Briefcase,
  TrendingUp,
  BarChart3,
} from 'lucide-react';

const TASK_TEMPLATES = [
  {
    name: 'Job Search Agent',
    instructions: `Search for job postings on LinkedIn and Indeed with the following criteria:

Job Titles: "AI Engineer", "ML Engineer", "LLM Engineer", "Full Stack Developer"
Keywords to look for: "Claude", "Anthropic", "LLM", "AI-Native", "Remote"
Keywords to avoid: "Senior Principal", "Director", "10+ years"

For each job found:
1. Score it from 0-100 based on how well it matches my criteria
2. Extract: job title, company name, location, salary if listed
3. Save jobs with score >= 60

After searching, send me a summary via Telegram with the top 10 matches, including:
- Job title and company
- Score and why you gave that score
- Direct link to apply`,
  },
  {
    name: 'News Monitor',
    instructions: `Monitor tech news for topics I care about:

Topics: "AI agents", "Claude", "Anthropic", "LLM tools", "AI coding assistants"

Every day:
1. Search for recent news articles (last 24 hours)
2. Read and summarize the most relevant ones
3. Score each article by relevance (0-100)
4. Save articles with score >= 70

Send me a daily digest via Telegram with:
- Article title and source
- 2-3 sentence summary
- Why it's relevant to me
- Link to read more`,
  },
  {
    name: 'Product Price Tracker',
    instructions: `Track prices for products I want to buy:

Products to track:
- [Add your product URLs here]

Every day:
1. Visit each product page
2. Extract current price
3. Compare to previous price
4. Save if there's a price drop

Alert me via Telegram when:
- Price drops by more than 10%
- Price reaches my target price

Include product name, current price, previous price, and link.`,
  },
];

export default function AgentTasksPage() {
  const params = useParams();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const workspaceId = Number(params.id);

  const [showCreate, setShowCreate] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState<typeof TASK_TEMPLATES[0] | null>(null);
  const [newTask, setNewTask] = useState({
    name: '',
    instructions: '',
    schedule: 'daily',
  });

  // Fetch workspace
  const { data: workspace } = useQuery({
    queryKey: ['workspace', workspaceId],
    queryFn: async () => {
      const response = await workspaceApi.get(workspaceId);
      return response.data;
    },
  });

  // Fetch tasks
  const { data: tasks, isLoading } = useQuery({
    queryKey: ['tasks', workspaceId],
    queryFn: async () => {
      const response = await agentTaskApi.list(workspaceId);
      return response.data.results || response.data;
    },
  });

  // Create task mutation
  const createTask = useMutation({
    mutationFn: (data: typeof newTask) => agentTaskApi.create(workspaceId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks', workspaceId] });
      setShowCreate(false);
      setNewTask({ name: '', instructions: '', schedule: 'daily' });
      toast({ title: 'Task created!' });
    },
    onError: () => {
      toast({ variant: 'destructive', title: 'Failed to create task' });
    },
  });

  // Run task mutation
  const runTask = useMutation({
    mutationFn: (taskId: number) => agentTaskApi.run(workspaceId, taskId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks', workspaceId] });
      toast({ title: 'Task execution started!' });
    },
    onError: (error: any) => {
      toast({
        variant: 'destructive',
        title: 'Failed to run task',
        description: error.response?.data?.error,
      });
    },
  });

  // Delete task mutation
  const deleteTask = useMutation({
    mutationFn: (taskId: number) => agentTaskApi.delete(workspaceId, taskId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks', workspaceId] });
      toast({ title: 'Task deleted' });
    },
  });

  const applyTemplate = (template: typeof TASK_TEMPLATES[0]) => {
    setSelectedTemplate(template);
    setNewTask({
      name: template.name,
      instructions: template.instructions,
      schedule: 'daily',
    });
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'running':
        return <Badge variant="warning"><Loader2 className="h-3 w-3 mr-1 animate-spin" />Running</Badge>;
      case 'completed':
        return <Badge variant="success"><CheckCircle className="h-3 w-3 mr-1" />Completed</Badge>;
      case 'failed':
        return <Badge variant="destructive"><XCircle className="h-3 w-3 mr-1" />Failed</Badge>;
      case 'paused':
        return <Badge variant="secondary"><Pause className="h-3 w-3 mr-1" />Paused</Badge>;
      default:
        return <Badge variant="secondary"><Clock className="h-3 w-3 mr-1" />Pending</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href={`/dashboard/workspaces/${workspaceId}`}>
            <Button variant="ghost" size="icon">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2">
              <ListTodo className="h-6 w-6" />
              Agent Tasks
            </h1>
            <p className="text-muted-foreground">{workspace?.name}</p>
          </div>
        </div>
        <Button onClick={() => setShowCreate(true)}>
          <Plus className="h-4 w-4 mr-2" />
          New Task
        </Button>
      </div>

      {/* Create Task Form */}
      {showCreate && (
        <Card>
          <CardHeader>
            <CardTitle>Create Agent Task</CardTitle>
            <CardDescription>
              Tell your agent what you want it to accomplish. Be specific about what to search for, how to score results, and where to send them.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Templates */}
            <div>
              <Label className="mb-2 block">Start from a template:</Label>
              <div className="flex gap-2 flex-wrap">
                {TASK_TEMPLATES.map((template) => (
                  <Button
                    key={template.name}
                    variant={selectedTemplate?.name === template.name ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => applyTemplate(template)}
                  >
                    {template.name}
                  </Button>
                ))}
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="name">Task Name</Label>
              <Input
                id="name"
                placeholder="e.g., Daily Job Search"
                value={newTask.name}
                onChange={(e) => setNewTask((prev) => ({ ...prev, name: e.target.value }))}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="instructions">Instructions</Label>
              <textarea
                id="instructions"
                className="w-full min-h-[200px] p-3 rounded-lg border bg-background resize-y font-mono text-sm"
                placeholder="Tell the agent exactly what you want it to do..."
                value={newTask.instructions}
                onChange={(e) => setNewTask((prev) => ({ ...prev, instructions: e.target.value }))}
              />
              <p className="text-xs text-muted-foreground">
                Be specific: what to search, how to score, where to send results
              </p>
            </div>

            <div className="space-y-2">
              <Label>Schedule</Label>
              <div className="flex gap-2">
                {[
                  { value: 'once', label: 'Run Once' },
                  { value: 'hourly', label: 'Hourly' },
                  { value: 'daily', label: 'Daily' },
                  { value: 'weekly', label: 'Weekly' },
                ].map((option) => (
                  <Button
                    key={option.value}
                    variant={newTask.schedule === option.value ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => setNewTask((prev) => ({ ...prev, schedule: option.value }))}
                  >
                    {option.label}
                  </Button>
                ))}
              </div>
            </div>

            <div className="flex gap-2">
              <Button
                onClick={() => createTask.mutate(newTask)}
                disabled={createTask.isPending || !newTask.name || !newTask.instructions}
              >
                {createTask.isPending ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <Plus className="h-4 w-4 mr-2" />
                )}
                Create Task
              </Button>
              <Button variant="outline" onClick={() => setShowCreate(false)}>
                Cancel
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Task List */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : tasks && tasks.length > 0 ? (
        <div className="space-y-4">
          {tasks.map((task: any) => (
            <Card key={task.id}>
              <CardContent className="p-6">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <h3 className="text-lg font-semibold">{task.name}</h3>
                      {getStatusBadge(task.status)}
                      <Badge variant="outline">{task.schedule}</Badge>
                    </div>

                    <p className="text-sm text-muted-foreground line-clamp-3 mb-4">
                      {task.instructions}
                    </p>

                    {/* Stats */}
                    <div className="flex gap-4 text-sm text-muted-foreground">
                      <span>Runs: {task.run_count}</span>
                      {task.last_run && (
                        <span>Last run: {new Date(task.last_run).toLocaleString()}</span>
                      )}
                    </div>

                    {/* Recent Results Preview */}
                    {task.recent_results && task.recent_results.length > 0 && (
                      <div className="mt-4 p-3 rounded-lg bg-muted/50 border">
                        <div className="flex items-center justify-between mb-3">
                          <div className="flex items-center gap-2">
                            <Briefcase className="h-4 w-4 text-muted-foreground" />
                            <span className="text-sm font-medium">Recent Results</span>
                          </div>
                          <Link href={`/dashboard/workspaces/${workspaceId}/tasks/${task.id}`}>
                            <Button size="sm" variant="ghost" className="h-7 text-xs">
                              View All <ExternalLink className="h-3 w-3 ml-1" />
                            </Button>
                          </Link>
                        </div>
                        <div className="space-y-2">
                          {task.recent_results.slice(0, 3).map((result: any) => (
                            <div
                              key={result.id}
                              className="flex items-center justify-between p-2 rounded bg-background border text-sm"
                            >
                              <div className="flex items-center gap-2 flex-1 min-w-0">
                                <span className="font-medium truncate">{result.title}</span>
                                {result.data?.company && (
                                  <span className="text-muted-foreground text-xs">@ {result.data.company}</span>
                                )}
                              </div>
                              <div className="flex items-center gap-2 flex-shrink-0">
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
                                    <TrendingUp className="h-3 w-3 mr-1" />
                                    {result.score}
                                  </Badge>
                                )}
                                {result.url && (
                                  <a
                                    href={result.url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-primary hover:underline"
                                  >
                                    <ExternalLink className="h-4 w-4" />
                                  </a>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                        {task.result_count > 3 && (
                          <Link href={`/dashboard/workspaces/${workspaceId}/tasks/${task.id}`}>
                            <p className="text-xs text-primary hover:underline text-center mt-2">
                              + {task.result_count - 3} more results
                            </p>
                          </Link>
                        )}
                      </div>
                    )}

                    {/* Error */}
                    {task.last_error && (
                      <div className="mt-4 p-2 rounded bg-destructive/10 text-destructive text-sm">
                        {task.last_error}
                      </div>
                    )}
                  </div>

                  {/* Actions */}
                  <div className="flex flex-col gap-2 ml-4">
                    <Button
                      size="sm"
                      onClick={() => runTask.mutate(task.id)}
                      disabled={runTask.isPending || task.status === 'running'}
                    >
                      {task.status === 'running' ? (
                        <>
                          <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                          Running
                        </>
                      ) : (
                        <>
                          <Play className="h-4 w-4 mr-1" />
                          Run
                        </>
                      )}
                    </Button>
                    <Link href={`/dashboard/workspaces/${workspaceId}/tasks/${task.id}`}>
                      <Button size="sm" variant="secondary" className="w-full">
                        <Eye className="h-4 w-4 mr-1" />
                        Results
                        {task.result_count > 0 && (
                          <Badge variant="outline" className="ml-1 text-xs">
                            {task.result_count}
                          </Badge>
                        )}
                      </Button>
                    </Link>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => {
                        if (confirm('Delete this task?')) {
                          deleteTask.mutate(task.id);
                        }
                      }}
                    >
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <ListTodo className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="font-medium mb-1">No tasks yet</h3>
            <p className="text-sm text-muted-foreground mb-4">
              Create a task to tell your agent what to do
            </p>
            <Button onClick={() => setShowCreate(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Create Your First Task
            </Button>
          </CardContent>
        </Card>
      )}

      {/* How it works */}
      <Card>
        <CardHeader>
          <CardTitle>How Agent Tasks Work</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-3">
            <div className="text-center p-4">
              <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-2">
                <span className="font-bold text-primary">1</span>
              </div>
              <h4 className="font-medium">Define Your Task</h4>
              <p className="text-sm text-muted-foreground">
                Tell the agent what to search for, how to score results, and where to send them
              </p>
            </div>
            <div className="text-center p-4">
              <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-2">
                <span className="font-bold text-primary">2</span>
              </div>
              <h4 className="font-medium">Agent Uses Tools</h4>
              <p className="text-sm text-muted-foreground">
                The AI agent uses web search, scraping, and other tools to accomplish your task
              </p>
            </div>
            <div className="text-center p-4">
              <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-2">
                <span className="font-bold text-primary">3</span>
              </div>
              <h4 className="font-medium">Get Results</h4>
              <p className="text-sm text-muted-foreground">
                Results are saved and sent to you via Telegram, Slack, or other connected channels
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
