'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { jobApplyApi } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Loader2,
  ArrowLeft,
  RefreshCw,
  FileText,
  ExternalLink,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import Link from 'next/link';

const statusColors: Record<string, string> = {
  queued: 'bg-yellow-500/10 text-yellow-600',
  generating_cover: 'bg-blue-500/10 text-blue-600',
  applying: 'bg-blue-500/10 text-blue-600',
  applied: 'bg-green-500/10 text-green-600',
  failed: 'bg-red-500/10 text-red-600',
  rejected: 'bg-red-500/10 text-red-600',
  interview: 'bg-purple-500/10 text-purple-600',
  offer: 'bg-emerald-500/10 text-emerald-600',
  withdrawn: 'bg-gray-500/10 text-gray-600',
};

const statusOptions = ['', 'queued', 'applied', 'failed', 'interview', 'offer', 'rejected'];

export default function ApplicationsPage() {
  const [statusFilter, setStatusFilter] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['jobapply-applications', statusFilter],
    queryFn: async () => {
      const params: any = {};
      if (statusFilter) params.status = statusFilter;
      const res = await jobApplyApi.listApplications(params);
      return res.data.results || res.data;
    },
  });

  const applications = data || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Link href="/dashboard/jobapply">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <div>
          <h1 className="text-2xl font-bold">Applications</h1>
          <p className="text-muted-foreground">
            {applications.length} total applications
          </p>
        </div>
      </div>

      {/* Status Filter */}
      <div className="flex flex-wrap gap-2">
        {statusOptions.map((s) => (
          <Button
            key={s}
            variant={statusFilter === s ? 'default' : 'outline'}
            size="sm"
            onClick={() => setStatusFilter(s)}
          >
            {s || 'All'}
          </Button>
        ))}
      </div>

      {/* Applications List */}
      {isLoading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : applications.length === 0 ? (
        <Card>
          <CardContent className="text-center py-12">
            <FileText className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <h3 className="font-medium mb-1">No applications</h3>
            <p className="text-sm text-muted-foreground">
              {statusFilter ? `No ${statusFilter} applications found` : 'Apply to jobs from the listings page'}
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {applications.map((app: any) => (
            <ApplicationCard key={app.id} application={app} />
          ))}
        </div>
      )}
    </div>
  );
}

function ApplicationCard({ application }: { application: any }) {
  const queryClient = useQueryClient();
  const [expanded, setExpanded] = useState(false);

  const retryMutation = useMutation({
    mutationFn: () => jobApplyApi.retryApplication(application.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobapply-applications'] });
    },
  });

  const regenerateMutation = useMutation({
    mutationFn: () => jobApplyApi.regenerateCover(application.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobapply-applications'] });
    },
  });

  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-center justify-between">
          <div className="flex-1 min-w-0">
            <h3 className="font-medium truncate">{application.listing_title}</h3>
            <p className="text-sm text-muted-foreground">{application.listing_company}</p>
          </div>
          <div className="flex items-center gap-2 ml-4">
            <Badge className={statusColors[application.status] || ''}>
              {application.status}
            </Badge>
            {application.listing_url && (
              <a href={application.listing_url} target="_blank" rel="noopener noreferrer">
                <Button variant="ghost" size="sm">
                  <ExternalLink className="h-4 w-4" />
                </Button>
              </a>
            )}
            {application.status === 'failed' && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => retryMutation.mutate()}
                disabled={retryMutation.isPending}
              >
                {retryMutation.isPending ? (
                  <Loader2 className="h-3 w-3 animate-spin" />
                ) : (
                  <RefreshCw className="h-3 w-3" />
                )}
              </Button>
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setExpanded(!expanded)}
            >
              {expanded ? (
                <ChevronUp className="h-4 w-4" />
              ) : (
                <ChevronDown className="h-4 w-4" />
              )}
            </Button>
          </div>
        </div>

        {expanded && (
          <div className="mt-4 space-y-3 border-t pt-3">
            {application.cover_letter && (
              <div>
                <div className="flex items-center justify-between mb-1">
                  <h4 className="text-sm font-medium">Cover Letter</h4>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => regenerateMutation.mutate()}
                    disabled={regenerateMutation.isPending}
                  >
                    {regenerateMutation.isPending ? (
                      <Loader2 className="h-3 w-3 animate-spin mr-1" />
                    ) : (
                      <RefreshCw className="h-3 w-3 mr-1" />
                    )}
                    Regenerate
                  </Button>
                </div>
                <div className="text-sm text-muted-foreground whitespace-pre-wrap bg-muted/50 p-3 rounded-md">
                  {application.cover_letter}
                </div>
              </div>
            )}
            {application.error_message && (
              <div>
                <h4 className="text-sm font-medium text-red-600">Error</h4>
                <p className="text-sm text-red-600/80">{application.error_message}</p>
              </div>
            )}
            <div className="text-xs text-muted-foreground">
              Created: {new Date(application.created_at).toLocaleDateString()}
              {application.applied_at && (
                <> | Applied: {new Date(application.applied_at).toLocaleDateString()}</>
              )}
              {application.applied_via && (
                <> | Via: {application.applied_via}</>
              )}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
