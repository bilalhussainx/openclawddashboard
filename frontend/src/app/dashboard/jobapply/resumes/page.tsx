'use client';

import { useState, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { jobApplyApi } from '@/lib/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import {
  Loader2,
  ArrowLeft,
  Upload,
  FileText,
  Star,
  Trash2,
  RefreshCw,
} from 'lucide-react';
import Link from 'next/link';

export default function ResumesPage() {
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploadName, setUploadName] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['jobapply-resumes'],
    queryFn: async () => {
      const res = await jobApplyApi.listResumes();
      return res.data.results || res.data;
    },
  });

  const uploadMutation = useMutation({
    mutationFn: (formData: FormData) => jobApplyApi.uploadResume(formData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobapply-resumes'] });
      setUploadName('');
      if (fileInputRef.current) fileInputRef.current.value = '';
    },
  });

  const handleUpload = () => {
    const file = fileInputRef.current?.files?.[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);
    formData.append('name', uploadName || file.name);
    uploadMutation.mutate(formData);
  };

  const resumes = data || [];

  return (
    <div className="space-y-6 max-w-2xl">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Link href="/dashboard/jobapply">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <h1 className="text-2xl font-bold">Resumes</h1>
      </div>

      {/* Upload */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Upload Resume</CardTitle>
          <CardDescription>PDF or DOCX files supported</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <Input
            placeholder="Resume name (optional)"
            value={uploadName}
            onChange={(e) => setUploadName(e.target.value)}
          />
          <div className="flex gap-2">
            <Input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx,.doc"
              className="flex-1"
            />
            <Button
              onClick={handleUpload}
              disabled={uploadMutation.isPending}
            >
              {uploadMutation.isPending ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Upload className="h-4 w-4 mr-2" />
              )}
              Upload
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Resumes List */}
      {isLoading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : resumes.length === 0 ? (
        <Card>
          <CardContent className="text-center py-12">
            <FileText className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <h3 className="font-medium mb-1">No resumes uploaded</h3>
            <p className="text-sm text-muted-foreground">
              Upload your resume to get started
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {resumes.map((resume: any) => (
            <ResumeCard key={resume.id} resume={resume} />
          ))}
        </div>
      )}
    </div>
  );
}

function ResumeCard({ resume }: { resume: any }) {
  const queryClient = useQueryClient();
  const [showParsed, setShowParsed] = useState(false);

  const parseMutation = useMutation({
    mutationFn: () => jobApplyApi.parseResume(resume.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobapply-resumes'] });
    },
  });

  const setPrimaryMutation = useMutation({
    mutationFn: () => jobApplyApi.setPrimaryResume(resume.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobapply-resumes'] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => jobApplyApi.deleteResume(resume.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobapply-resumes'] });
    },
  });

  const skills = resume.parsed_data?.skills || [];

  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <FileText className="h-5 w-5 text-primary" />
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-medium">{resume.name}</h3>
                {resume.is_primary && (
                  <Badge className="bg-yellow-500/10 text-yellow-600">Primary</Badge>
                )}
              </div>
              <p className="text-xs text-muted-foreground">
                {resume.file_type.toUpperCase()} | Uploaded {new Date(resume.created_at).toLocaleDateString()}
              </p>
            </div>
          </div>
          <div className="flex gap-1">
            {!resume.is_primary && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setPrimaryMutation.mutate()}
                disabled={setPrimaryMutation.isPending}
                title="Set as primary"
              >
                <Star className="h-4 w-4" />
              </Button>
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={() => parseMutation.mutate()}
              disabled={parseMutation.isPending}
              title="Re-parse with AI"
            >
              {parseMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <RefreshCw className="h-4 w-4" />
              )}
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => deleteMutation.mutate()}
              disabled={deleteMutation.isPending}
              title="Delete"
            >
              <Trash2 className="h-4 w-4 text-red-500" />
            </Button>
          </div>
        </div>

        {skills.length > 0 && (
          <div className="mt-3">
            <div className="flex flex-wrap gap-1">
              {skills.slice(0, showParsed ? undefined : 8).map((skill: string) => (
                <Badge key={skill} variant="secondary" className="text-xs">
                  {skill}
                </Badge>
              ))}
              {skills.length > 8 && !showParsed && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-xs h-5"
                  onClick={() => setShowParsed(true)}
                >
                  +{skills.length - 8} more
                </Button>
              )}
            </div>
          </div>
        )}

        {showParsed && resume.parsed_data && (
          <div className="mt-3 text-sm text-muted-foreground border-t pt-3 space-y-1">
            {resume.parsed_data.name && <p><strong>Name:</strong> {resume.parsed_data.name}</p>}
            {resume.parsed_data.location && <p><strong>Location:</strong> {resume.parsed_data.location}</p>}
            {resume.parsed_data.summary && <p><strong>Summary:</strong> {resume.parsed_data.summary}</p>}
            {resume.parsed_data.experience?.map((exp: any, i: number) => (
              <p key={i}><strong>{exp.title}</strong> at {exp.company} ({exp.dates})</p>
            ))}
            <Button
              variant="ghost"
              size="sm"
              className="text-xs"
              onClick={() => setShowParsed(false)}
            >
              Show less
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
