'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { jobApplyApi } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import {
  Search,
  Loader2,
  ExternalLink,
  TrendingUp,
  X,
  ArrowLeft,
  Filter,
  CheckCircle,
  Bot,
} from 'lucide-react';
import Link from 'next/link';

export default function ListingsPage() {
  const queryClient = useQueryClient();
  const [minScore, setMinScore] = useState<number | undefined>();
  const [sourceFilter, setSourceFilter] = useState<string>('');

  const { data, isLoading } = useQuery({
    queryKey: ['jobapply-listings', minScore, sourceFilter],
    queryFn: async () => {
      const params: any = { page_size: 500 };
      if (minScore) params.min_score = minScore;
      if (sourceFilter) params.source = sourceFilter;
      const res = await jobApplyApi.listListings(params);
      return res.data.results || res.data;
    },
  });

  const searchMutation = useMutation({
    mutationFn: () => jobApplyApi.searchNow(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobapply-listings'] });
    },
  });

  const listings = data || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link href="/dashboard/jobapply">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <div>
            <h1 className="text-2xl font-bold">Job Listings</h1>
            <p className="text-muted-foreground">
              {listings.length} jobs found
            </p>
          </div>
        </div>
        <Button
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
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="flex flex-wrap items-center gap-3 p-4">
          <Filter className="h-4 w-4 text-muted-foreground" />
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">Min Score:</span>
            <Input
              type="number"
              min={0}
              max={100}
              placeholder="0"
              className="w-20 h-8"
              value={minScore || ''}
              onChange={(e) => setMinScore(e.target.value ? parseInt(e.target.value) : undefined)}
            />
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">Source:</span>
            {[
              { id: '', label: 'All' },
              { id: 'linkedin', label: 'LinkedIn' },
              { id: 'indeed', label: 'Indeed' },
              { id: 'glassdoor', label: 'Glassdoor' },
              { id: 'hn_hiring', label: 'HN Hiring' },
              { id: 'remoteok', label: 'RemoteOK' },
            ].map((src) => (
              <Button
                key={src.id}
                variant={sourceFilter === src.id ? 'default' : 'outline'}
                size="sm"
                onClick={() => setSourceFilter(src.id)}
              >
                {src.label}
              </Button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Listings */}
      {isLoading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : listings.length === 0 ? (
        <Card>
          <CardContent className="text-center py-12">
            <Search className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <h3 className="font-medium mb-1">No listings found</h3>
            <p className="text-sm text-muted-foreground mb-4">
              Try adjusting your filters or run a new search
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {listings.map((listing: any) => (
            <ListingCard key={listing.id} listing={listing} />
          ))}
        </div>
      )}
    </div>
  );
}

function ListingCard({ listing }: { listing: any }) {
  const queryClient = useQueryClient();
  const [applyStatus, setApplyStatus] = useState<string>('');

  const applyMutation = useMutation({
    mutationFn: () => jobApplyApi.applyToListing(listing.id),
    onSuccess: () => {
      setApplyStatus('Application queued - AI agent is filling the form and uploading your resume...');
      // Open the job URL so user can verify
      if (listing.url) {
        window.open(listing.url, '_blank', 'noopener,noreferrer');
      }
      queryClient.invalidateQueries({ queryKey: ['jobapply-listings'] });
    },
    onError: (err: any) => {
      const msg = err?.response?.data?.error || 'Failed to queue application';
      setApplyStatus(msg);
    },
  });

  const dismissMutation = useMutation({
    mutationFn: () => jobApplyApi.dismissListing(listing.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobapply-listings'] });
    },
  });

  const scoreColor =
    listing.match_score >= 80 ? 'text-green-600 bg-green-500/10' :
    listing.match_score >= 60 ? 'text-yellow-600 bg-yellow-500/10' :
    'text-red-600 bg-red-500/10';

  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <h3 className="font-medium truncate">{listing.title}</h3>
              <Badge variant="outline" className="shrink-0 text-xs">
                {listing.source_board}
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground mb-2">
              {listing.company}
              {listing.location && ` - ${listing.location}`}
              {listing.salary_info && ` | ${listing.salary_info}`}
            </p>
            {listing.description && (
              <p className="text-sm text-muted-foreground line-clamp-2">
                {listing.description}
              </p>
            )}
            {listing.matched_keywords?.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-2">
                {listing.matched_keywords.map((kw: string) => (
                  <Badge key={kw} variant="secondary" className="text-xs">
                    {kw}
                  </Badge>
                ))}
              </div>
            )}
            {applyStatus && (
              <div className="mt-2 flex items-center gap-2 text-sm bg-blue-500/10 text-blue-600 px-3 py-2 rounded-md">
                <Bot className="h-4 w-4 shrink-0" />
                {applyStatus}
              </div>
            )}
          </div>

          <div className="flex flex-col items-end gap-2 shrink-0">
            <div className={`flex items-center gap-1 px-2 py-1 rounded-md ${scoreColor}`}>
              <TrendingUp className="h-4 w-4" />
              <span className="font-bold">{listing.match_score}</span>
            </div>

            <div className="flex gap-1">
              {listing.url && (
                <a href={listing.url} target="_blank" rel="noopener noreferrer">
                  <Button variant="ghost" size="sm">
                    <ExternalLink className="h-4 w-4" />
                  </Button>
                </a>
              )}
              <Button
                variant="ghost"
                size="sm"
                onClick={() => dismissMutation.mutate()}
                disabled={dismissMutation.isPending}
              >
                <X className="h-4 w-4" />
              </Button>
              {listing.has_application ? (
                <div className="flex flex-col items-end gap-1">
                  <Badge className={
                    listing.application_info?.applied_via === 'manual'
                      ? 'bg-yellow-500/10 text-yellow-600 self-center'
                      : 'bg-green-500/10 text-green-600 self-center'
                  }>
                    <CheckCircle className="h-3 w-3 mr-1" />
                    {listing.application_info?.applied_via === 'manual' ? 'Manual' :
                     listing.application_info?.applied_via ? `Via ${listing.application_info.applied_via}` :
                     'Applied'}
                  </Badge>
                  {listing.application_info?.error_message && (
                    <span className="text-xs text-muted-foreground max-w-[200px] text-right">
                      {listing.application_info.error_message.slice(0, 80)}
                    </span>
                  )}
                </div>
              ) : (
                <Button
                  size="sm"
                  onClick={() => applyMutation.mutate()}
                  disabled={applyMutation.isPending || !!applyStatus}
                >
                  {applyMutation.isPending ? (
                    <Loader2 className="h-3 w-3 animate-spin" />
                  ) : (
                    'Apply'
                  )}
                </Button>
              )}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
