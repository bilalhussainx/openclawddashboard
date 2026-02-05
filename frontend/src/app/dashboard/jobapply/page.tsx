'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Link from 'next/link';
import { jobApplyApi } from '@/lib/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Briefcase,
  Search,
  FileText,
  CheckCircle2,
  XCircle,
  Clock,
  ArrowRight,
  Loader2,
  Star,
  TrendingUp,
  RefreshCw,
} from 'lucide-react';

const statusColors: Record<string, string> = {
  queued: 'bg-yellow-500/10 text-yellow-600',
  generating_cover: 'bg-blue-500/10 text-blue-600',
  applying: 'bg-blue-500/10 text-blue-600',
  applied: 'bg-green-500/10 text-green-600',
  failed: 'bg-red-500/10 text-red-600',
  rejected: 'bg-red-500/10 text-red-600',
  interview: 'bg-purple-500/10 text-purple-600',
  offer: 'bg-emerald-500/10 text-emerald-600',
};

export default function JobApplyDashboard() {
  const queryClient = useQueryClient();

  const { data: dashboard, isLoading } = useQuery({
    queryKey: ['jobapply-dashboard'],
    queryFn: async () => {
      const res = await jobApplyApi.dashboard();
      return res.data;
    },
  });

  const searchMutation = useMutation({
    mutationFn: () => jobApplyApi.searchNow(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobapply-dashboard'] });
    },
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Job Auto-Apply</h1>
          <p className="text-muted-foreground">
            Automated job search, scoring, and application
          </p>
        </div>
        <div className="flex space-x-2">
          <Button
            variant="outline"
            onClick={() => searchMutation.mutate()}
            disabled={searchMutation.isPending}
          >
            {searchMutation.isPending ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Search className="h-4 w-4 mr-2" />
            )}
            Search Now
          </Button>
          <Link href="/dashboard/jobapply/preferences">
            <Button variant="outline">
              <RefreshCw className="h-4 w-4 mr-2" />
              Preferences
            </Button>
          </Link>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Jobs Found</CardTitle>
            <Search className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{dashboard?.total_listings || 0}</div>
            <p className="text-xs text-muted-foreground">
              Avg score: {Math.round(dashboard?.avg_match_score || 0)}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Applications</CardTitle>
            <Briefcase className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{dashboard?.total_applications || 0}</div>
            <p className="text-xs text-muted-foreground">
              {dashboard?.applied_count || 0} applied
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Interviews</CardTitle>
            <Star className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{dashboard?.interview_count || 0}</div>
            <p className="text-xs text-muted-foreground">Scheduled</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Failed</CardTitle>
            <XCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{dashboard?.failed_count || 0}</div>
            <p className="text-xs text-muted-foreground">Can retry</p>
          </CardContent>
        </Card>
      </div>

      {/* Recent Listings */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Recent Job Matches</CardTitle>
            <CardDescription>Highest scoring jobs found</CardDescription>
          </div>
          <Link href="/dashboard/jobapply/listings">
            <Button variant="outline" size="sm">
              View All
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </Link>
        </CardHeader>
        <CardContent>
          {!dashboard?.recent_listings?.length ? (
            <div className="text-center py-8">
              <Search className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <h3 className="font-medium mb-1">No jobs found yet</h3>
              <p className="text-sm text-muted-foreground mb-4">
                Click &quot;Search Now&quot; to find matching jobs
              </p>
              <Button onClick={() => searchMutation.mutate()} disabled={searchMutation.isPending}>
                <Search className="h-4 w-4 mr-2" />
                Start Job Search
              </Button>
            </div>
          ) : (
            <div className="space-y-3">
              {dashboard.recent_listings.map((listing: any) => (
                <div
                  key={listing.id}
                  className="flex items-center justify-between p-3 rounded-lg border hover:bg-muted/50 transition-colors"
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <h4 className="font-medium truncate">{listing.title}</h4>
                      <Badge variant="outline" className="shrink-0">
                        {listing.source_board}
                      </Badge>
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {listing.company} {listing.location && `- ${listing.location}`}
                    </p>
                  </div>
                  <div className="flex items-center gap-3 ml-4">
                    <div className="flex items-center gap-1">
                      <TrendingUp className="h-4 w-4 text-muted-foreground" />
                      <span className={`text-sm font-medium ${
                        listing.match_score >= 80 ? 'text-green-600' :
                        listing.match_score >= 60 ? 'text-yellow-600' : 'text-red-600'
                      }`}>
                        {listing.match_score}
                      </span>
                    </div>
                    {listing.has_application ? (
                      <Badge className="bg-green-500/10 text-green-600">Applied</Badge>
                    ) : (
                      <ApplyButton listingId={listing.id} />
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Recent Applications */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Recent Applications</CardTitle>
            <CardDescription>Track your application statuses</CardDescription>
          </div>
          <Link href="/dashboard/jobapply/applications">
            <Button variant="outline" size="sm">
              View All
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </Link>
        </CardHeader>
        <CardContent>
          {!dashboard?.recent_applications?.length ? (
            <div className="text-center py-8">
              <FileText className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <h3 className="font-medium mb-1">No applications yet</h3>
              <p className="text-sm text-muted-foreground">
                Apply to jobs from the listings page
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {dashboard.recent_applications.map((app: any) => (
                <div
                  key={app.id}
                  className="flex items-center justify-between p-3 rounded-lg border"
                >
                  <div className="flex-1 min-w-0">
                    <h4 className="font-medium truncate">{app.listing_title}</h4>
                    <p className="text-sm text-muted-foreground">{app.listing_company}</p>
                  </div>
                  <div className="flex items-center gap-2 ml-4">
                    <Badge className={statusColors[app.status] || ''}>
                      {app.status}
                    </Badge>
                    {app.status === 'failed' && (
                      <RetryButton applicationId={app.id} />
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Quick Links */}
      <div className="grid gap-4 md:grid-cols-3">
        <Link href="/dashboard/jobapply/resumes">
          <Card className="hover:bg-muted/50 transition-colors cursor-pointer">
            <CardContent className="flex items-center space-x-3 p-4">
              <FileText className="h-5 w-5 text-primary" />
              <div>
                <p className="font-medium">Manage Resumes</p>
                <p className="text-sm text-muted-foreground">Upload and parse resumes</p>
              </div>
            </CardContent>
          </Card>
        </Link>
        <Link href="/dashboard/jobapply/preferences">
          <Card className="hover:bg-muted/50 transition-colors cursor-pointer">
            <CardContent className="flex items-center space-x-3 p-4">
              <RefreshCw className="h-5 w-5 text-primary" />
              <div>
                <p className="font-medium">Job Preferences</p>
                <p className="text-sm text-muted-foreground">Keywords, location, boards</p>
              </div>
            </CardContent>
          </Card>
        </Link>
        <Link href="/dashboard/jobapply/listings">
          <Card className="hover:bg-muted/50 transition-colors cursor-pointer">
            <CardContent className="flex items-center space-x-3 p-4">
              <Search className="h-5 w-5 text-primary" />
              <div>
                <p className="font-medium">Browse Jobs</p>
                <p className="text-sm text-muted-foreground">View all discovered listings</p>
              </div>
            </CardContent>
          </Card>
        </Link>
      </div>
    </div>
  );
}

function ApplyButton({ listingId }: { listingId: number }) {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: () => jobApplyApi.applyToListing(listingId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobapply-dashboard'] });
    },
  });

  return (
    <Button
      size="sm"
      variant="outline"
      onClick={() => mutation.mutate()}
      disabled={mutation.isPending}
    >
      {mutation.isPending ? (
        <Loader2 className="h-3 w-3 animate-spin" />
      ) : (
        'Apply'
      )}
    </Button>
  );
}

function RetryButton({ applicationId }: { applicationId: number }) {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: () => jobApplyApi.retryApplication(applicationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobapply-dashboard'] });
    },
  });

  return (
    <Button
      size="sm"
      variant="ghost"
      onClick={() => mutation.mutate()}
      disabled={mutation.isPending}
    >
      {mutation.isPending ? (
        <Loader2 className="h-3 w-3 animate-spin" />
      ) : (
        <RefreshCw className="h-3 w-3" />
      )}
    </Button>
  );
}
