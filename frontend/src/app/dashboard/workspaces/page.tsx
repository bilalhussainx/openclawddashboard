'use client';

import { useEffect } from 'react';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { workspaceApi } from '@/lib/api';
import { useWorkspaceStore, Workspace } from '@/stores/workspace';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Box, Plus, ArrowRight, Loader2 } from 'lucide-react';

export default function WorkspacesPage() {
  const { setWorkspaces } = useWorkspaceStore();

  const { data: workspacesData, isLoading } = useQuery({
    queryKey: ['workspaces'],
    queryFn: async () => {
      const response = await workspaceApi.list();
      return response.data.results || response.data;
    },
  });

  useEffect(() => {
    if (workspacesData) {
      setWorkspaces(workspacesData);
    }
  }, [workspacesData, setWorkspaces]);

  const workspaces: Workspace[] = workspacesData || [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Workspaces</h1>
          <p className="text-muted-foreground">Manage your AI assistant deployments</p>
        </div>
        <Link href="/dashboard/workspaces/new">
          <Button>
            <Plus className="h-4 w-4 mr-2" />
            New Workspace
          </Button>
        </Link>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : workspaces.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Box className="h-12 w-12 text-muted-foreground mb-4" />
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
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {workspaces.map((workspace) => (
            <Link key={workspace.id} href={`/dashboard/workspaces/${workspace.id}`}>
              <Card className="hover:bg-muted/50 transition-colors cursor-pointer h-full">
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
                      <Box className="h-5 w-5 text-primary" />
                    </div>
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
                  </div>
                  <CardTitle className="mt-3">{workspace.name}</CardTitle>
                  <CardDescription>{workspace.description || 'No description'}</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">
                      {workspace.channels.length} channel{workspace.channels.length !== 1 ? 's' : ''}
                    </span>
                    <span className="text-muted-foreground">{workspace.model_display}</span>
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
