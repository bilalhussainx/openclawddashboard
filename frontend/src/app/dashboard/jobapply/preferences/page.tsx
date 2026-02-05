'use client';

import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { jobApplyApi } from '@/lib/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  Loader2,
  ArrowLeft,
  Save,
  Plus,
  X,
} from 'lucide-react';
import Link from 'next/link';

export default function PreferencesPage() {
  const queryClient = useQueryClient();

  const { data: prefs, isLoading } = useQuery({
    queryKey: ['jobapply-preferences'],
    queryFn: async () => {
      const res = await jobApplyApi.getPreferences();
      return res.data;
    },
  });

  const [keywords, setKeywords] = useState<string[]>([]);
  const [excludedKeywords, setExcludedKeywords] = useState<string[]>([]);
  const [location, setLocation] = useState('Toronto');
  const [remoteOk, setRemoteOk] = useState(true);
  const [enabledBoards, setEnabledBoards] = useState<string[]>([]);
  const [autoApplyEnabled, setAutoApplyEnabled] = useState(false);
  const [autoApplyMinScore, setAutoApplyMinScore] = useState(70);
  const [maxDailyApplications, setMaxDailyApplications] = useState(15);
  const [newKeyword, setNewKeyword] = useState('');
  const [newExcluded, setNewExcluded] = useState('');

  useEffect(() => {
    if (prefs) {
      setKeywords(prefs.keywords || []);
      setExcludedKeywords(prefs.excluded_keywords || []);
      setLocation(prefs.location || 'Toronto');
      setRemoteOk(prefs.remote_ok ?? true);
      setEnabledBoards(prefs.enabled_boards || []);
      setAutoApplyEnabled(prefs.auto_apply_enabled ?? false);
      setAutoApplyMinScore(prefs.auto_apply_min_score ?? 70);
      setMaxDailyApplications(prefs.max_daily_applications ?? 15);
    }
  }, [prefs]);

  const saveMutation = useMutation({
    mutationFn: (data: object) => jobApplyApi.updatePreferences(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobapply-preferences'] });
    },
  });

  const handleSave = () => {
    saveMutation.mutate({
      keywords,
      excluded_keywords: excludedKeywords,
      location,
      remote_ok: remoteOk,
      enabled_boards: enabledBoards,
      auto_apply_enabled: autoApplyEnabled,
      auto_apply_min_score: autoApplyMinScore,
      max_daily_applications: maxDailyApplications,
    });
  };

  const addKeyword = () => {
    if (newKeyword.trim() && !keywords.includes(newKeyword.trim())) {
      setKeywords([...keywords, newKeyword.trim()]);
      setNewKeyword('');
    }
  };

  const addExcluded = () => {
    if (newExcluded.trim() && !excludedKeywords.includes(newExcluded.trim())) {
      setExcludedKeywords([...excludedKeywords, newExcluded.trim()]);
      setNewExcluded('');
    }
  };

  const jobspyBoards = [
    { id: 'linkedin', label: 'LinkedIn' },
    { id: 'indeed', label: 'Indeed' },
    { id: 'glassdoor', label: 'Glassdoor' },
    { id: 'zip_recruiter', label: 'ZipRecruiter' },
    { id: 'google', label: 'Google Jobs' },
  ];
  const startupBoards = [
    { id: 'hn_hiring', label: "HN Who's Hiring" },
    { id: 'remoteok', label: 'RemoteOK' },
  ];

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-2xl">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link href="/dashboard/jobapply">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <h1 className="text-2xl font-bold">Job Preferences</h1>
        </div>
        <Button onClick={handleSave} disabled={saveMutation.isPending}>
          {saveMutation.isPending ? (
            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
          ) : (
            <Save className="h-4 w-4 mr-2" />
          )}
          Save
        </Button>
      </div>

      {saveMutation.isSuccess && (
        <div className="text-sm text-green-600 bg-green-500/10 px-3 py-2 rounded-md">
          Preferences saved successfully
        </div>
      )}

      {/* Search Keywords */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Search Keywords</CardTitle>
          <CardDescription>Job titles and keywords to search for</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex flex-wrap gap-2">
            {keywords.map((kw) => (
              <Badge key={kw} variant="secondary" className="text-sm py-1 px-2">
                {kw}
                <button
                  className="ml-1 hover:text-red-500"
                  onClick={() => setKeywords(keywords.filter((k) => k !== kw))}
                >
                  <X className="h-3 w-3" />
                </button>
              </Badge>
            ))}
          </div>
          <div className="flex gap-2">
            <Input
              placeholder="Add keyword..."
              value={newKeyword}
              onChange={(e) => setNewKeyword(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && addKeyword()}
            />
            <Button variant="outline" onClick={addKeyword}>
              <Plus className="h-4 w-4" />
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Excluded Keywords */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Excluded Keywords</CardTitle>
          <CardDescription>Jobs containing these will be penalized in scoring</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex flex-wrap gap-2">
            {excludedKeywords.map((kw) => (
              <Badge key={kw} variant="outline" className="text-sm py-1 px-2 text-red-600">
                {kw}
                <button
                  className="ml-1 hover:text-red-500"
                  onClick={() => setExcludedKeywords(excludedKeywords.filter((k) => k !== kw))}
                >
                  <X className="h-3 w-3" />
                </button>
              </Badge>
            ))}
          </div>
          <div className="flex gap-2">
            <Input
              placeholder="Add excluded keyword..."
              value={newExcluded}
              onChange={(e) => setNewExcluded(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && addExcluded()}
            />
            <Button variant="outline" onClick={addExcluded}>
              <Plus className="h-4 w-4" />
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Location */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Location</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <Input
            placeholder="City or region"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
          />
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={remoteOk}
              onChange={(e) => setRemoteOk(e.target.checked)}
              className="rounded"
            />
            Include remote jobs
          </label>
        </CardContent>
      </Card>

      {/* Job Boards */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Job Boards</CardTitle>
          <CardDescription>Select which boards to search</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <p className="text-sm font-medium text-muted-foreground mb-2">Traditional Boards</p>
            <div className="flex flex-wrap gap-2">
              {jobspyBoards.map((board) => (
                <Button
                  key={board.id}
                  variant={enabledBoards.includes(board.id) ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => {
                    if (enabledBoards.includes(board.id)) {
                      setEnabledBoards(enabledBoards.filter((b) => b !== board.id));
                    } else {
                      setEnabledBoards([...enabledBoards, board.id]);
                    }
                  }}
                >
                  {board.label}
                </Button>
              ))}
            </div>
          </div>
          <div>
            <p className="text-sm font-medium text-muted-foreground mb-2">Startup / AI Boards</p>
            <div className="flex flex-wrap gap-2">
              {startupBoards.map((board) => (
                <Button
                  key={board.id}
                  variant={enabledBoards.includes(board.id) ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => {
                    if (enabledBoards.includes(board.id)) {
                      setEnabledBoards(enabledBoards.filter((b) => b !== board.id));
                    } else {
                      setEnabledBoards([...enabledBoards, board.id]);
                    }
                  }}
                >
                  {board.label}
                </Button>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Auto-Apply Settings */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Auto-Apply</CardTitle>
          <CardDescription>Automatically apply to high-scoring jobs</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={autoApplyEnabled}
              onChange={(e) => setAutoApplyEnabled(e.target.checked)}
              className="rounded"
            />
            Enable auto-apply
          </label>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm text-muted-foreground">Min Score to Apply</label>
              <Input
                type="number"
                min={0}
                max={100}
                value={autoApplyMinScore}
                onChange={(e) => setAutoApplyMinScore(parseInt(e.target.value) || 70)}
              />
            </div>
            <div>
              <label className="text-sm text-muted-foreground">Max Daily Applications</label>
              <Input
                type="number"
                min={1}
                max={50}
                value={maxDailyApplications}
                onChange={(e) => setMaxDailyApplications(parseInt(e.target.value) || 15)}
              />
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
