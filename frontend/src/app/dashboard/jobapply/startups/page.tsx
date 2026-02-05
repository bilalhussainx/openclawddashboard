'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { jobApplyApi } from '@/lib/api';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Loader2,
  ArrowLeft,
  Search,
  ExternalLink,
  TrendingUp,
  X,
  Sparkles,
  Rocket,
  CheckCircle,
  Bot,
} from 'lucide-react';
import Link from 'next/link';

const AI_TERMS = [
  'ai', 'artificial intelligence', 'machine learning', 'ml', 'llm',
  'large language model', 'claude', 'anthropic', 'openai', 'gpt',
  'ai native', 'ai-native', 'generative ai', 'gen ai',
  'nlp', 'deep learning',
];

function hasAiMention(listing: any): boolean {
  const text = `${listing.title} ${listing.description} ${listing.company}`.toLowerCase();
  return AI_TERMS.some((term) => text.includes(term));
}

const TIME_FILTERS = [
  { label: '24h', value: 24 },
  { label: '48h', value: 48 },
  { label: '7d', value: 168 },
  { label: '30d', value: 720 },
  { label: 'All', value: 0 },
];

export default function StartupJobsPage() {
  const queryClient = useQueryClient();
  const [hoursFilter, setHoursFilter] = useState(48);

  const { data, isLoading } = useQuery({
    queryKey: ['startup-listings', hoursFilter],
    queryFn: async () => {
      const params: any = { page_size: 500 };
      if (hoursFilter > 0) params.hours = hoursFilter;
      const res = await jobApplyApi.listStartupListings(params);
      return res.data.results || res.data;
    },
  });

  const searchMutation = useMutation({
    mutationFn: () => jobApplyApi.searchStartups(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['startup-listings'] });
    },
  });

  const allListings = data || [];

  // Sort: AI jobs first, then by score descending
  const listings = [...allListings].sort((a: any, b: any) => {
    const aAi = hasAiMention(a) ? 1 : 0;
    const bAi = hasAiMention(b) ? 1 : 0;
    if (bAi !== aAi) return bAi - aAi;
    return (b.match_score || 0) - (a.match_score || 0);
  });

  const aiCount = listings.filter((l: any) => hasAiMention(l)).length;

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
            <h1 className="text-2xl font-bold flex items-center gap-2">
              <Rocket className="h-6 w-6" />
              Startup Jobs
            </h1>
            <p className="text-muted-foreground">
              {listings.length} jobs from HN & RemoteOK
              {aiCount > 0 && ` | ${aiCount} mention AI tools`}
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
          Search Startups
        </Button>
      </div>

      {/* Time Filter */}
      <Card>
        <CardContent className="flex items-center gap-3 p-4">
          <span className="text-sm text-muted-foreground">Posted within:</span>
          {TIME_FILTERS.map((tf) => (
            <Button
              key={tf.value}
              variant={hoursFilter === tf.value ? 'default' : 'outline'}
              size="sm"
              onClick={() => setHoursFilter(tf.value)}
            >
              {tf.label}
            </Button>
          ))}
        </CardContent>
      </Card>

      {searchMutation.isPending && (
        <div className="text-sm text-muted-foreground bg-blue-500/10 px-3 py-2 rounded-md">
          Searching HN Who&apos;s Hiring and RemoteOK... This runs in the background.
          Results will appear shortly.
        </div>
      )}

      {/* Listings */}
      {isLoading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : listings.length === 0 ? (
        <Card>
          <CardContent className="text-center py-12">
            <Rocket className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <h3 className="font-medium mb-1">No startup jobs found</h3>
            <p className="text-sm text-muted-foreground mb-4">
              Click &quot;Search Startups&quot; to fetch jobs from HN Who&apos;s Hiring and RemoteOK.
              Make sure hn_hiring and remoteok are enabled in your preferences.
            </p>
            <Link href="/dashboard/jobapply/preferences">
              <Button variant="outline" size="sm">
                Open Preferences
              </Button>
            </Link>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {listings.map((listing: any) => (
            <StartupListingCard key={listing.id} listing={listing} />
          ))}
        </div>
      )}
    </div>
  );
}

function StartupListingCard({ listing }: { listing: any }) {
  const queryClient = useQueryClient();
  const isAi = hasAiMention(listing);
  const [applyStatus, setApplyStatus] = useState<string>('');

  const applyMutation = useMutation({
    mutationFn: () => jobApplyApi.applyToListing(listing.id),
    onSuccess: () => {
      setApplyStatus('Application queued - AI agent is filling the form and uploading your resume...');
      if (listing.url) {
        window.open(listing.url, '_blank', 'noopener,noreferrer');
      }
      queryClient.invalidateQueries({ queryKey: ['startup-listings'] });
    },
    onError: (err: any) => {
      const msg = err?.response?.data?.error || 'Failed to queue application';
      setApplyStatus(msg);
    },
  });

  const dismissMutation = useMutation({
    mutationFn: () => jobApplyApi.dismissListing(listing.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['startup-listings'] });
    },
  });

  const scoreColor =
    listing.match_score >= 80 ? 'text-green-600 bg-green-500/10' :
    listing.match_score >= 60 ? 'text-yellow-600 bg-yellow-500/10' :
    'text-red-600 bg-red-500/10';

  const sourceLabel =
    listing.source_board === 'hn_hiring' ? 'HN Hiring' :
    listing.source_board === 'remoteok' ? 'RemoteOK' :
    listing.source_board;

  return (
    <Card className={isAi ? 'border-purple-500/30' : ''}>
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <h3 className="font-medium truncate">{listing.title}</h3>
              <Badge variant="outline" className="shrink-0 text-xs">
                {sourceLabel}
              </Badge>
              {isAi && (
                <Badge className="shrink-0 text-xs bg-purple-500/10 text-purple-600">
                  <Sparkles className="h-3 w-3 mr-1" />
                  AI
                </Badge>
              )}
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
                <Badge className="bg-green-500/10 text-green-600 self-center">
                  <CheckCircle className="h-3 w-3 mr-1" />
                  Applied
                </Badge>
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
