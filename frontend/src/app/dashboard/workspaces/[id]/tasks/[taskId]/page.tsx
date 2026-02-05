'use client';

import { useState, useMemo } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { workspaceApi, agentTaskApi } from '@/lib/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { useToast } from '@/components/ui/use-toast';
import {
  ArrowLeft,
  Play,
  Loader2,
  ExternalLink,
  Star,
  Building,
  MapPin,
  DollarSign,
  Clock,
  Bookmark,
  BookmarkCheck,
  Search,
  Briefcase,
  Tag,
  TrendingUp,
  FileText,
  Code,
  Brain,
  Globe,
  Cat,
  Database,
  Terminal,
  CheckCircle,
  Copy,
  Link as LinkIcon,
} from 'lucide-react';

interface TaskResult {
  id: number;
  result_type: string;
  title: string;
  url: string;
  score: number | null;
  summary: string;
  is_saved: boolean;
  found_at: string;
  data: Record<string, any>;
}

// Icons for different result types
const RESULT_TYPE_CONFIG: Record<string, { icon: any; label: string; color: string }> = {
  job: { icon: Briefcase, label: 'Jobs', color: 'text-blue-500' },
  article: { icon: FileText, label: 'Articles', color: 'text-green-500' },
  code: { icon: Code, label: 'Code', color: 'text-purple-500' },
  fact: { icon: Cat, label: 'Facts', color: 'text-orange-500' },
  webpage: { icon: Globe, label: 'Web Pages', color: 'text-cyan-500' },
  memory: { icon: Brain, label: 'Memory', color: 'text-pink-500' },
  preference: { icon: Star, label: 'Preferences', color: 'text-yellow-500' },
  interest: { icon: Tag, label: 'Interests', color: 'text-indigo-500' },
  database: { icon: Database, label: 'Database', color: 'text-red-500' },
  shell: { icon: Terminal, label: 'Commands', color: 'text-gray-500' },
};

export default function TaskResultsPage() {
  const params = useParams();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const workspaceId = Number(params.id);
  const taskId = Number(params.taskId);

  const [searchQuery, setSearchQuery] = useState('');
  const [filterSaved, setFilterSaved] = useState(false);
  const [sortBy, setSortBy] = useState<'score' | 'date'>('date');
  const [minScore, setMinScore] = useState(0);
  const [selectedType, setSelectedType] = useState<string | null>(null);

  // Fetch workspace
  const { data: workspace } = useQuery({
    queryKey: ['workspace', workspaceId],
    queryFn: async () => {
      const response = await workspaceApi.get(workspaceId);
      return response.data;
    },
  });

  // Fetch task
  const { data: task } = useQuery({
    queryKey: ['task', workspaceId, taskId],
    queryFn: async () => {
      const response = await agentTaskApi.get(workspaceId, taskId);
      return response.data;
    },
  });

  // Fetch results
  const { data: resultsData, isLoading } = useQuery({
    queryKey: ['taskResults', workspaceId, taskId],
    queryFn: async () => {
      const response = await agentTaskApi.getResults(workspaceId, taskId);
      return response.data;
    },
    refetchInterval: task?.status === 'running' ? 5000 : false,
  });

  // Run task mutation
  const runTask = useMutation({
    mutationFn: () => agentTaskApi.run(workspaceId, taskId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['task', workspaceId, taskId] });
      queryClient.invalidateQueries({ queryKey: ['taskResults', workspaceId, taskId] });
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

  const results: TaskResult[] = resultsData?.results || [];

  // Analyze result types
  const resultTypes = useMemo(() => {
    const types: Record<string, number> = {};
    results.forEach((r) => {
      const type = r.result_type || 'other';
      types[type] = (types[type] || 0) + 1;
    });
    return types;
  }, [results]);

  // Determine primary result type
  const primaryType = useMemo(() => {
    if (Object.keys(resultTypes).length === 0) return null;
    return Object.entries(resultTypes).sort((a, b) => b[1] - a[1])[0][0];
  }, [resultTypes]);

  // Check if this is a job-focused task
  const isJobTask = primaryType === 'job' || task?.name?.toLowerCase().includes('job');

  // Filter and sort results
  const filteredResults = useMemo(() => {
    return results
      .filter((r) => {
        if (filterSaved && !r.is_saved) return false;
        if (selectedType && r.result_type !== selectedType) return false;
        if (minScore > 0 && (r.score || 0) < minScore) return false;
        if (searchQuery) {
          const query = searchQuery.toLowerCase();
          return (
            r.title?.toLowerCase().includes(query) ||
            r.summary?.toLowerCase().includes(query) ||
            JSON.stringify(r.data).toLowerCase().includes(query)
          );
        }
        return true;
      })
      .sort((a, b) => {
        if (sortBy === 'score') {
          return (b.score || 0) - (a.score || 0);
        }
        return new Date(b.found_at).getTime() - new Date(a.found_at).getTime();
      });
  }, [results, filterSaved, selectedType, minScore, searchQuery, sortBy]);

  // Stats for current view
  const stats = useMemo(() => {
    const hasScores = results.some((r) => r.score !== null);
    return {
      total: results.length,
      highScore: results.filter((r) => (r.score || 0) >= 70).length,
      saved: results.filter((r) => r.is_saved).length,
      hasScores,
    };
  }, [results]);

  const getResultTypeConfig = (type: string) => {
    return RESULT_TYPE_CONFIG[type] || { icon: FileText, label: type, color: 'text-gray-500' };
  };

  const getScoreBadge = (score: number | null) => {
    if (score === null || score === undefined) return null;
    if (score >= 70) {
      return (
        <Badge className="bg-green-500 hover:bg-green-600">
          <Star className="h-3 w-3 mr-1 fill-current" />
          {score}
        </Badge>
      );
    }
    if (score >= 40) {
      return (
        <Badge className="bg-yellow-500 hover:bg-yellow-600">
          <TrendingUp className="h-3 w-3 mr-1" />
          {score}
        </Badge>
      );
    }
    return <Badge variant="secondary">{score}</Badge>;
  };

  // Render result card based on type
  const renderResultCard = (result: TaskResult) => {
    const config = getResultTypeConfig(result.result_type);
    const Icon = config.icon;

    // Job-specific card
    if (result.result_type === 'job') {
      return (
        <Card key={result.id} className="hover:border-primary/50 transition-colors">
          <CardContent className="p-4">
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-2">
                  <Icon className={`h-5 w-5 ${config.color}`} />
                  <h3 className="font-semibold truncate">{result.title}</h3>
                  {getScoreBadge(result.score)}
                </div>
                <div className="flex flex-wrap gap-3 text-sm text-muted-foreground mb-2">
                  {result.data.company && (
                    <span className="flex items-center gap-1">
                      <Building className="h-4 w-4" />
                      {result.data.company}
                    </span>
                  )}
                  {result.data.location && (
                    <span className="flex items-center gap-1">
                      <MapPin className="h-4 w-4" />
                      {result.data.location}
                    </span>
                  )}
                  {result.data.salary && (
                    <span className="flex items-center gap-1 text-green-600">
                      <DollarSign className="h-4 w-4" />
                      {result.data.salary}
                    </span>
                  )}
                  {result.data.is_remote && <Badge variant="secondary">Remote</Badge>}
                </div>
                {result.data.description && (
                  <p className="text-sm text-muted-foreground line-clamp-2">{result.data.description}</p>
                )}
                <div className="flex items-center gap-2 mt-2 text-xs text-muted-foreground">
                  <span>{result.data.source || 'Unknown source'}</span>
                  <span>•</span>
                  <span>{new Date(result.found_at).toLocaleDateString()}</span>
                </div>
              </div>
              <div className="flex flex-col gap-2">
                {result.url && (
                  <a href={result.url} target="_blank" rel="noopener noreferrer">
                    <Button size="sm">
                      <ExternalLink className="h-4 w-4 mr-1" />
                      Apply
                    </Button>
                  </a>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      );
    }

    // Article/Web search card
    if (result.result_type === 'article' || result.result_type === 'webpage') {
      return (
        <Card key={result.id} className="hover:border-primary/50 transition-colors">
          <CardContent className="p-4">
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-2">
                  <Icon className={`h-5 w-5 ${config.color}`} />
                  <h3 className="font-semibold">{result.title}</h3>
                  {getScoreBadge(result.score)}
                </div>
                {result.summary && (
                  <p className="text-sm text-muted-foreground mb-2">{result.summary}</p>
                )}
                {result.url && (
                  <p className="text-xs text-blue-500 truncate">{result.url}</p>
                )}
                <div className="flex items-center gap-2 mt-2 text-xs text-muted-foreground">
                  <Clock className="h-3 w-3" />
                  <span>{new Date(result.found_at).toLocaleString()}</span>
                </div>
              </div>
              <div className="flex flex-col gap-2">
                {result.url && (
                  <a href={result.url} target="_blank" rel="noopener noreferrer">
                    <Button size="sm" variant="outline">
                      <ExternalLink className="h-4 w-4 mr-1" />
                      Open
                    </Button>
                  </a>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      );
    }

    // Code execution card
    if (result.result_type === 'code') {
      return (
        <Card key={result.id} className="hover:border-primary/50 transition-colors">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 mb-3">
              <Icon className={`h-5 w-5 ${config.color}`} />
              <h3 className="font-semibold">{result.title}</h3>
              <Badge variant="outline" className="ml-auto">
                <CheckCircle className="h-3 w-3 mr-1 text-green-500" />
                Executed
              </Badge>
            </div>
            {result.data.code && (
              <pre className="bg-muted p-3 rounded-lg text-sm overflow-x-auto mb-3">
                <code>{result.data.code}</code>
              </pre>
            )}
            {result.data.output && (
              <div className="bg-black/90 text-green-400 p-3 rounded-lg text-sm font-mono overflow-x-auto">
                {result.data.output}
              </div>
            )}
            {result.summary && !result.data.code && (
              <p className="text-sm text-muted-foreground">{result.summary}</p>
            )}
          </CardContent>
        </Card>
      );
    }

    // Fact card (cat facts, etc.)
    if (result.result_type === 'fact') {
      return (
        <Card key={result.id} className="hover:border-primary/50 transition-colors">
          <CardContent className="p-4">
            <div className="flex items-start gap-3">
              <div className="h-10 w-10 rounded-full bg-orange-100 flex items-center justify-center">
                <Cat className="h-5 w-5 text-orange-500" />
              </div>
              <div className="flex-1">
                <h3 className="font-semibold mb-1">{result.title}</h3>
                <p className="text-sm text-muted-foreground">{result.summary || result.data.fact}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      );
    }

    // Memory/preference/interest cards
    if (['memory', 'preference', 'interest'].includes(result.result_type)) {
      return (
        <Card key={result.id} className="hover:border-primary/50 transition-colors">
          <CardContent className="p-4">
            <div className="flex items-start gap-3">
              <div className={`h-10 w-10 rounded-full bg-muted flex items-center justify-center`}>
                <Icon className={`h-5 w-5 ${config.color}`} />
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <h3 className="font-semibold">{result.title}</h3>
                  <Badge variant="outline">{config.label}</Badge>
                  {getScoreBadge(result.score)}
                </div>
                <p className="text-sm text-muted-foreground">{result.summary}</p>
                <p className="text-xs text-muted-foreground mt-2">
                  Stored: {new Date(result.found_at).toLocaleString()}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      );
    }

    // Generic card for other types
    return (
      <Card key={result.id} className="hover:border-primary/50 transition-colors">
        <CardContent className="p-4">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-2">
                <Icon className={`h-5 w-5 ${config.color}`} />
                <Badge variant="outline">{config.label}</Badge>
                <h3 className="font-semibold truncate">{result.title}</h3>
                {getScoreBadge(result.score)}
              </div>
              {result.summary && (
                <p className="text-sm text-muted-foreground mb-2">{result.summary}</p>
              )}
              {Object.keys(result.data).length > 0 && (
                <details className="text-xs">
                  <summary className="cursor-pointer text-muted-foreground hover:text-foreground">
                    View data
                  </summary>
                  <pre className="mt-2 p-2 bg-muted rounded text-xs overflow-auto max-h-40">
                    {JSON.stringify(result.data, null, 2)}
                  </pre>
                </details>
              )}
              <div className="flex items-center gap-2 mt-2 text-xs text-muted-foreground">
                <Clock className="h-3 w-3" />
                <span>{new Date(result.found_at).toLocaleString()}</span>
              </div>
            </div>
            {result.url && (
              <a href={result.url} target="_blank" rel="noopener noreferrer">
                <Button size="sm" variant="outline">
                  <ExternalLink className="h-4 w-4" />
                </Button>
              </a>
            )}
          </div>
        </CardContent>
      </Card>
    );
  };

  return (
    <div className="space-y-6">
      {/* Breadcrumb Navigation */}
      <nav className="flex items-center text-sm text-muted-foreground">
        <Link href="/dashboard" className="hover:text-foreground">Dashboard</Link>
        <span className="mx-2">/</span>
        <Link href={`/dashboard/workspaces/${workspaceId}`} className="hover:text-foreground">
          {workspace?.name || 'Workspace'}
        </Link>
        <span className="mx-2">/</span>
        <Link href={`/dashboard/workspaces/${workspaceId}/tasks`} className="hover:text-foreground">Tasks</Link>
        <span className="mx-2">/</span>
        <span className="text-foreground font-medium">{task?.name || 'Results'}</span>
      </nav>

      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href={`/dashboard/workspaces/${workspaceId}/tasks`}>
            <Button variant="ghost" size="icon">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2">
              {primaryType && (() => {
                const config = getResultTypeConfig(primaryType);
                const Icon = config.icon;
                return <Icon className={`h-6 w-6 ${config.color}`} />;
              })()}
              {task?.name || 'Task Results'}
            </h1>
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <span>{workspace?.name}</span>
              {task?.status && (
                <Badge
                  variant={
                    task.status === 'running' ? 'warning' : task.status === 'completed' ? 'success' : 'secondary'
                  }
                >
                  {task.status === 'running' && <Loader2 className="h-3 w-3 mr-1 animate-spin" />}
                  {task.status}
                </Badge>
              )}
            </div>
          </div>
        </div>
        <Button onClick={() => runTask.mutate()} disabled={runTask.isPending || task?.status === 'running'}>
          {task?.status === 'running' ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              Running...
            </>
          ) : (
            <>
              <Play className="h-4 w-4 mr-2" />
              Run Now
            </>
          )}
        </Button>
      </div>

      {/* Dynamic Stats */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <FileText className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm text-muted-foreground">Total Results</span>
            </div>
            <p className="text-2xl font-bold">{stats.total}</p>
          </CardContent>
        </Card>

        {/* Result Type Breakdown */}
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2 mb-2">
              <Tag className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm text-muted-foreground">Result Types</span>
            </div>
            <div className="flex flex-wrap gap-1">
              {Object.entries(resultTypes).map(([type, count]) => {
                const config = getResultTypeConfig(type);
                return (
                  <Badge
                    key={type}
                    variant={selectedType === type ? 'default' : 'outline'}
                    className="cursor-pointer"
                    onClick={() => setSelectedType(selectedType === type ? null : type)}
                  >
                    {config.label}: {count}
                  </Badge>
                );
              })}
            </div>
          </CardContent>
        </Card>

        {/* Show score stats only if results have scores */}
        {stats.hasScores && (
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center gap-2">
                <Star className="h-4 w-4 text-yellow-500" />
                <span className="text-sm text-muted-foreground">High Score (70+)</span>
              </div>
              <p className="text-2xl font-bold text-green-600">{stats.highScore}</p>
            </CardContent>
          </Card>
        )}

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <Clock className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm text-muted-foreground">Last Run</span>
            </div>
            <p className="text-sm font-medium">
              {task?.last_run ? new Date(task.last_run).toLocaleString() : 'Never'}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Task Output (if available) */}
      {task?.last_result && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <CheckCircle className="h-4 w-4 text-green-500" />
              Task Summary
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground whitespace-pre-wrap">{task.last_result}</p>
          </CardContent>
        </Card>
      )}

      {/* Filters - only show relevant ones */}
      {results.length > 0 && (
        <Card>
          <CardContent className="p-4">
            <div className="flex flex-wrap gap-4 items-center">
              <div className="flex-1 min-w-[200px]">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    placeholder="Search results..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-10"
                  />
                </div>
              </div>

              {stats.hasScores && (
                <div className="flex items-center gap-2">
                  <span className="text-sm text-muted-foreground">Min Score:</span>
                  <Input
                    type="number"
                    min={0}
                    max={100}
                    value={minScore}
                    onChange={(e) => setMinScore(Number(e.target.value))}
                    className="w-20"
                  />
                </div>
              )}

              <div className="flex gap-2">
                {stats.hasScores && (
                  <Button
                    variant={sortBy === 'score' ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => setSortBy('score')}
                  >
                    <Star className="h-4 w-4 mr-1" />
                    By Score
                  </Button>
                )}
                <Button
                  variant={sortBy === 'date' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setSortBy('date')}
                >
                  <Clock className="h-4 w-4 mr-1" />
                  By Date
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Results List */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : filteredResults.length > 0 ? (
        <div className="space-y-4">{filteredResults.map((result) => renderResultCard(result))}</div>
      ) : (
        <Card className={task?.status === 'running' ? 'border-primary/50 animate-pulse' : ''}>
          <CardContent className="flex flex-col items-center justify-center py-12">
            {task?.status === 'running' ? (
              <>
                <Loader2 className="h-12 w-12 text-primary mb-4 animate-spin" />
                <h3 className="font-medium mb-1">Task is running...</h3>
                <p className="text-sm text-muted-foreground mb-4 text-center">
                  Results will appear here automatically when ready.
                </p>
              </>
            ) : (
              <>
                <FileText className="h-12 w-12 text-muted-foreground mb-4" />
                <h3 className="font-medium mb-1">No results yet</h3>
                <p className="text-sm text-muted-foreground mb-4 text-center">
                  {results.length === 0
                    ? 'Click "Run Now" to execute this task.'
                    : 'No results match your current filters.'}
                </p>
                {results.length === 0 && (
                  <Button onClick={() => runTask.mutate()} disabled={runTask.isPending}>
                    {runTask.isPending ? (
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    ) : (
                      <Play className="h-4 w-4 mr-2" />
                    )}
                    Run Task Now
                  </Button>
                )}
              </>
            )}
          </CardContent>
        </Card>
      )}

      {/* Score Legend - only show for job tasks with scores */}
      {isJobTask && stats.hasScores && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">AI Tools Match Score</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-6 text-sm">
              <div className="flex items-center gap-2">
                <Badge className="bg-green-500">70-100</Badge>
                <span>High Match - Mentions Claude Code, Copilot, Cursor</span>
              </div>
              <div className="flex items-center gap-2">
                <Badge className="bg-yellow-500">40-69</Badge>
                <span>Moderate - AI/LLM related keywords</span>
              </div>
              <div className="flex items-center gap-2">
                <Badge variant="secondary">0-39</Badge>
                <span>Low Match - General posting</span>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
