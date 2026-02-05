'use client';

import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { workspaceApi } from '@/lib/api';
import { Workspace } from '@/stores/workspace';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { MessageSquare, Plus, ArrowRight, Loader2 } from 'lucide-react';

const channelColors: Record<string, string> = {
  telegram: 'bg-blue-500',
  slack: 'bg-purple-500',
  discord: 'bg-indigo-500',
  whatsapp: 'bg-green-500',
  teams: 'bg-blue-600',
};

export default function ChannelsPage() {
  const { data: workspaces, isLoading } = useQuery<Workspace[]>({
    queryKey: ['workspaces'],
    queryFn: async () => {
      const response = await workspaceApi.list();
      return response.data.results || response.data;
    },
  });

  const allChannels = workspaces?.flatMap((w) =>
    w.channels.map((c) => ({ ...c, workspace: w }))
  ) || [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Channels</h1>
        <p className="text-muted-foreground">View and manage all connected messaging channels</p>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : allChannels.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <MessageSquare className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="font-medium mb-1">No channels connected</h3>
            <p className="text-sm text-muted-foreground mb-4">
              Connect messaging channels to your workspaces
            </p>
            <Link href="/dashboard/workspaces">
              <Button>
                Go to Workspaces
                <ArrowRight className="h-4 w-4 ml-2" />
              </Button>
            </Link>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {allChannels.map((channel) => (
            <Link
              key={`${channel.workspace.id}-${channel.id}`}
              href={`/dashboard/workspaces/${channel.workspace.id}`}
            >
              <Card className="hover:bg-muted/50 transition-colors cursor-pointer h-full">
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <div className={`h-10 w-10 rounded-lg ${channelColors[channel.channel_type] || 'bg-gray-500'} flex items-center justify-center`}>
                      <MessageSquare className="h-5 w-5 text-white" />
                    </div>
                    <Badge variant={channel.is_active ? 'success' : 'secondary'}>
                      {channel.is_active ? 'Active' : 'Inactive'}
                    </Badge>
                  </div>
                  <CardTitle className="mt-3">{channel.channel_type_display}</CardTitle>
                  <CardDescription>{channel.workspace.name}</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center justify-between text-sm text-muted-foreground">
                    <span>
                      {channel.allowlist?.length || 0} allowed users
                    </span>
                    <span>
                      {channel.respond_to_groups ? 'Groups enabled' : 'DMs only'}
                    </span>
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}

      {/* Quick Add Section */}
      <Card>
        <CardHeader>
          <CardTitle>Add a Channel</CardTitle>
          <CardDescription>Connect a new messaging platform to your workspace</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {[
              { id: 'telegram', name: 'Telegram', color: 'bg-blue-500' },
              { id: 'slack', name: 'Slack', color: 'bg-purple-500' },
              { id: 'discord', name: 'Discord', color: 'bg-indigo-500', disabled: true },
              { id: 'whatsapp', name: 'WhatsApp', color: 'bg-green-500', disabled: true },
            ].map((platform) => (
              <div
                key={platform.id}
                className={`flex items-center gap-3 p-4 rounded-lg border ${platform.disabled ? 'opacity-50' : 'hover:bg-muted/50 cursor-pointer'}`}
              >
                <div className={`h-10 w-10 rounded-lg ${platform.color} flex items-center justify-center`}>
                  <MessageSquare className="h-5 w-5 text-white" />
                </div>
                <div>
                  <p className="font-medium">{platform.name}</p>
                  <p className="text-xs text-muted-foreground">
                    {platform.disabled ? 'Coming soon' : 'Available'}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
