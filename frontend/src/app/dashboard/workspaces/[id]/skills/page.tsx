'use client';

import { useParams } from 'next/navigation';
import Link from 'next/link';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { workspaceApi } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useToast } from '@/components/ui/use-toast';
import {
  ArrowLeft,
  Puzzle,
  Loader2,
  Trash2,
  AlertTriangle,
  CheckCircle,
  Clock,
  XCircle,
  Key,
  Settings,
  Plus,
} from 'lucide-react';

interface InstalledSkill {
  id: number;
  skill_slug: string;
  skill_name: string;
  skill_icon: string | null;
  is_enabled: boolean;
  install_status: string;
  install_status_display: string;
  install_error: string;
  clawhub_installed: boolean;
  installed_at: string;
  missing_requirements: string[];
  required_env: string[];
}

interface SkillStatusResponse {
  workspace_id: number;
  workspace_name: string;
  skills: InstalledSkill[];
  total_count: number;
  ready_count: number;
}

export default function WorkspaceSkillsPage() {
  const params = useParams();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const workspaceId = Number(params.id);

  const { data: skillStatus, isLoading } = useQuery<SkillStatusResponse>({
    queryKey: ['workspace-skills', workspaceId],
    queryFn: async () => {
      const response = await workspaceApi.skillStatus(workspaceId);
      return response.data;
    },
  });

  const uninstallMutation = useMutation({
    mutationFn: (installedSkillId: number) =>
      workspaceApi.uninstallSkill(workspaceId, installedSkillId),
    onSuccess: () => {
      toast({ title: 'Skill uninstalled' });
      queryClient.invalidateQueries({ queryKey: ['workspace-skills', workspaceId] });
    },
    onError: (error: any) => {
      toast({
        variant: 'destructive',
        title: 'Failed to uninstall',
        description: error.response?.data?.error || 'Something went wrong',
      });
    },
  });

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'ready':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'pending':
      case 'installing':
        return <Clock className="h-4 w-4 text-yellow-500" />;
      case 'error':
        return <XCircle className="h-4 w-4 text-red-500" />;
      case 'missing_reqs':
        return <AlertTriangle className="h-4 w-4 text-yellow-500" />;
      default:
        return <Clock className="h-4 w-4 text-muted-foreground" />;
    }
  };

  const getStatusVariant = (status: string) => {
    switch (status) {
      case 'ready':
        return 'success';
      case 'pending':
      case 'installing':
        return 'warning';
      case 'error':
      case 'missing_reqs':
        return 'destructive';
      default:
        return 'secondary';
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <Link
            href={`/dashboard/workspaces/${workspaceId}`}
            className="flex items-center text-sm text-muted-foreground hover:text-foreground mb-2"
          >
            <ArrowLeft className="h-4 w-4 mr-1" />
            Back to Workspace
          </Link>
          <h1 className="text-2xl font-bold">Installed Skills</h1>
          <p className="text-muted-foreground">
            {skillStatus?.workspace_name} - {skillStatus?.ready_count || 0} of {skillStatus?.total_count || 0} skills ready
          </p>
        </div>
        <Link href="/dashboard/skills">
          <Button>
            <Plus className="h-4 w-4 mr-2" />
            Browse Skills
          </Button>
        </Link>
      </div>

      {/* Skills List */}
      {skillStatus?.skills && skillStatus.skills.length > 0 ? (
        <div className="space-y-4">
          {skillStatus.skills.map((skill) => (
            <Card key={skill.id}>
              <CardContent className="p-6">
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-4">
                    <div className="h-12 w-12 rounded-lg bg-primary/10 flex items-center justify-center">
                      <Puzzle className="h-6 w-6 text-primary" />
                    </div>
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <h3 className="font-semibold">{skill.skill_name}</h3>
                        <Badge variant={getStatusVariant(skill.install_status) as any}>
                          {getStatusIcon(skill.install_status)}
                          <span className="ml-1">{skill.install_status_display}</span>
                        </Badge>
                      </div>
                      <p className="text-sm text-muted-foreground">
                        Installed {new Date(skill.installed_at).toLocaleDateString()}
                      </p>

                      {/* Missing Requirements Warning */}
                      {skill.missing_requirements.length > 0 && (
                        <div className="mt-3 rounded-lg border border-yellow-500/50 bg-yellow-500/10 p-3">
                          <div className="flex items-start gap-2">
                            <AlertTriangle className="h-4 w-4 text-yellow-600 mt-0.5" />
                            <div className="space-y-1">
                              <p className="text-sm font-medium text-yellow-600">
                                Missing API Keys
                              </p>
                              <div className="flex flex-wrap gap-2">
                                {skill.missing_requirements.map((env) => (
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

                      {/* Error Message */}
                      {skill.install_error && (
                        <div className="mt-3 rounded-lg border border-red-500/50 bg-red-500/10 p-3">
                          <p className="text-sm text-red-600">{skill.install_error}</p>
                        </div>
                      )}
                    </div>
                  </div>

                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-destructive hover:text-destructive"
                    onClick={() => {
                      if (confirm('Are you sure you want to uninstall this skill?')) {
                        uninstallMutation.mutate(skill.id);
                      }
                    }}
                    disabled={uninstallMutation.isPending}
                  >
                    {uninstallMutation.isPending ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Trash2 className="h-4 w-4" />
                    )}
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Puzzle className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="font-medium mb-1">No skills installed</h3>
            <p className="text-sm text-muted-foreground mb-4">
              Install skills from the marketplace to extend your agent's capabilities
            </p>
            <Link href="/dashboard/skills">
              <Button>
                <Plus className="h-4 w-4 mr-2" />
                Browse Skills
              </Button>
            </Link>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
