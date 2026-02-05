'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { workspaceApi, skillApi } from '@/lib/api';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useToast } from '@/components/ui/use-toast';
import { Loader2, AlertTriangle, Key, Settings } from 'lucide-react';
import Link from 'next/link';

interface Skill {
  id: number;
  name: string;
  slug: string;
  description: string;
  required_env?: string[];
}

interface Workspace {
  id: number;
  name: string;
  status: string;
}

interface InstallSkillDialogProps {
  skill: Skill | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function InstallSkillDialog({
  skill,
  open,
  onOpenChange,
}: InstallSkillDialogProps) {
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState<string>('');
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const { data: workspaces, isLoading: isLoadingWorkspaces } = useQuery<Workspace[]>({
    queryKey: ['workspaces'],
    queryFn: async () => {
      const response = await workspaceApi.list();
      return response.data.results || response.data;
    },
    enabled: open,
  });

  const installMutation = useMutation({
    mutationFn: async () => {
      if (!skill || !selectedWorkspaceId) return;
      const response = await skillApi.install(skill.slug, Number(selectedWorkspaceId));
      return response.data;
    },
    onSuccess: (data) => {
      toast({
        title: 'Skill installed',
        description: data?.missing_requirements?.length
          ? `${skill?.name} installed but requires API key configuration`
          : `${skill?.name} has been installed successfully`,
      });
      queryClient.invalidateQueries({ queryKey: ['workspace', Number(selectedWorkspaceId)] });
      queryClient.invalidateQueries({ queryKey: ['skills'] });
      onOpenChange(false);
      setSelectedWorkspaceId('');
    },
    onError: (error: any) => {
      toast({
        variant: 'destructive',
        title: 'Installation failed',
        description: error.response?.data?.error || 'Something went wrong',
      });
    },
  });

  const hasRequiredEnv = skill?.required_env && skill.required_env.length > 0;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Install {skill?.name}</DialogTitle>
          <DialogDescription>
            Select a workspace to install this skill to.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Workspace Selector */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Workspace</label>
            {isLoadingWorkspaces ? (
              <div className="flex items-center justify-center py-4">
                <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
              </div>
            ) : workspaces && workspaces.length > 0 ? (
              <Select
                value={selectedWorkspaceId}
                onValueChange={setSelectedWorkspaceId}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select a workspace" />
                </SelectTrigger>
                <SelectContent>
                  {workspaces.map((workspace) => (
                    <SelectItem key={workspace.id} value={String(workspace.id)}>
                      {workspace.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            ) : (
              <div className="text-center py-4 text-sm text-muted-foreground">
                <p>No workspaces found.</p>
                <Link href="/dashboard/workspaces/new" className="text-primary hover:underline">
                  Create a workspace first
                </Link>
              </div>
            )}
          </div>

          {/* Required API Keys Warning */}
          {hasRequiredEnv && (
            <div className="rounded-lg border border-yellow-500/50 bg-yellow-500/10 p-4">
              <div className="flex items-start gap-3">
                <AlertTriangle className="h-5 w-5 text-yellow-600 mt-0.5" />
                <div className="space-y-2">
                  <p className="text-sm font-medium text-yellow-600">
                    API Keys Required
                  </p>
                  <p className="text-xs text-muted-foreground">
                    This skill requires the following API keys to function:
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {skill?.required_env?.map((env) => (
                      <Badge key={env} variant="outline" className="text-xs">
                        <Key className="h-3 w-3 mr-1" />
                        {env}
                      </Badge>
                    ))}
                  </div>
                  <Link
                    href="/dashboard/settings"
                    className="inline-flex items-center text-xs text-primary hover:underline"
                  >
                    <Settings className="h-3 w-3 mr-1" />
                    Configure in Settings
                  </Link>
                </div>
              </div>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => {
              onOpenChange(false);
              setSelectedWorkspaceId('');
            }}
          >
            Cancel
          </Button>
          <Button
            onClick={() => installMutation.mutate()}
            disabled={!selectedWorkspaceId || installMutation.isPending}
          >
            {installMutation.isPending && (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            )}
            Install
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
