'use client';

import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { gmailApi } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  ArrowLeft,
  Mail,
  CheckCircle,
  XCircle,
  Loader2,
  ExternalLink,
  RefreshCw,
  Unlink,
} from 'lucide-react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';

export default function IntegrationsPage() {
  const queryClient = useQueryClient();
  const searchParams = useSearchParams();
  const [statusMessage, setStatusMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Check for OAuth callback result
  useEffect(() => {
    const success = searchParams.get('success');
    const error = searchParams.get('error');

    if (success === 'true') {
      setStatusMessage({ type: 'success', text: 'Gmail connected successfully!' });
      queryClient.invalidateQueries({ queryKey: ['gmail-connection'] });
    } else if (error) {
      setStatusMessage({ type: 'error', text: `Connection failed: ${error}` });
    }

    // Clear URL params after reading
    if (success || error) {
      window.history.replaceState({}, '', '/dashboard/jobapply/integrations');
    }
  }, [searchParams, queryClient]);

  // Fetch Gmail connection status
  const { data: gmailConnection, isLoading } = useQuery({
    queryKey: ['gmail-connection'],
    queryFn: async () => {
      const res = await gmailApi.getConnection();
      return res.data;
    },
  });

  // Connect Gmail mutation
  const connectMutation = useMutation({
    mutationFn: async () => {
      const res = await gmailApi.getOAuthUrl();
      return res.data.oauth_url;
    },
    onSuccess: (oauthUrl) => {
      // Redirect to Google OAuth
      window.location.href = oauthUrl;
    },
    onError: (err: any) => {
      setStatusMessage({
        type: 'error',
        text: err?.response?.data?.error || 'Failed to start OAuth flow',
      });
    },
  });

  // Disconnect Gmail mutation
  const disconnectMutation = useMutation({
    mutationFn: () => gmailApi.disconnect(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['gmail-connection'] });
      setStatusMessage({ type: 'success', text: 'Gmail disconnected' });
    },
  });

  // Test connection mutation
  const testMutation = useMutation({
    mutationFn: () => gmailApi.test(),
    onSuccess: (res) => {
      const data = res.data;
      if (data.status === 'connected') {
        setStatusMessage({
          type: 'success',
          text: `Connection working! Found ${data.recent_emails} recent emails.`,
        });
      } else {
        setStatusMessage({
          type: 'error',
          text: 'Connection test failed - no emails found or not connected.',
        });
      }
    },
    onError: () => {
      setStatusMessage({ type: 'error', text: 'Connection test failed' });
    },
  });

  const isConnected = gmailConnection?.is_connected;

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
          <h1 className="text-2xl font-bold">Integrations</h1>
          <p className="text-muted-foreground">
            Connect external services for enhanced job application automation
          </p>
        </div>
      </div>

      {/* Status Message */}
      {statusMessage && (
        <div
          className={`px-4 py-3 rounded-md ${
            statusMessage.type === 'success'
              ? 'bg-green-500/10 text-green-600'
              : 'bg-red-500/10 text-red-600'
          }`}
        >
          <div className="flex items-center gap-2">
            {statusMessage.type === 'success' ? (
              <CheckCircle className="h-4 w-4" />
            ) : (
              <XCircle className="h-4 w-4" />
            )}
            {statusMessage.text}
          </div>
        </div>
      )}

      {/* Gmail Integration Card */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-red-500/10">
                <Mail className="h-6 w-6 text-red-500" />
              </div>
              <div>
                <CardTitle className="flex items-center gap-2">
                  Gmail
                  {isLoading ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : isConnected ? (
                    <Badge className="bg-green-500/10 text-green-600">Connected</Badge>
                  ) : (
                    <Badge variant="outline">Not Connected</Badge>
                  )}
                </CardTitle>
                <CardDescription>
                  Read Greenhouse verification codes from your email automatically
                </CardDescription>
              </div>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {isConnected ? (
            <>
              <div className="flex items-center gap-2 text-sm">
                <CheckCircle className="h-4 w-4 text-green-500" />
                <span>Connected as: <strong>{gmailConnection.email_address}</strong></span>
              </div>

              <div className="text-sm text-muted-foreground">
                When you apply to a Greenhouse job that requires email verification,
                we&apos;ll automatically fetch the security code from your Gmail and complete
                the application for you.
              </div>

              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => testMutation.mutate()}
                  disabled={testMutation.isPending}
                >
                  {testMutation.isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  ) : (
                    <RefreshCw className="h-4 w-4 mr-2" />
                  )}
                  Test Connection
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => disconnectMutation.mutate()}
                  disabled={disconnectMutation.isPending}
                  className="text-red-600 hover:text-red-700"
                >
                  {disconnectMutation.isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  ) : (
                    <Unlink className="h-4 w-4 mr-2" />
                  )}
                  Disconnect
                </Button>
              </div>
            </>
          ) : (
            <>
              <div className="text-sm text-muted-foreground">
                Connect your Gmail to enable automatic Greenhouse verification code handling.
                When Greenhouse sends a security code to verify your application, we&apos;ll
                read it from your inbox and complete the submission automatically.
              </div>

              <div className="text-sm text-muted-foreground bg-muted/50 p-3 rounded-md">
                <strong>Permissions needed:</strong>
                <ul className="list-disc list-inside mt-1">
                  <li>Read your email messages (gmail.readonly)</li>
                  <li>See your email address</li>
                </ul>
                <p className="mt-2 text-xs">
                  We only search for emails from greenhouse.io containing verification codes.
                  We don&apos;t read or store any other emails.
                </p>
              </div>

              <Button
                onClick={() => connectMutation.mutate()}
                disabled={connectMutation.isPending}
              >
                {connectMutation.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                ) : (
                  <ExternalLink className="h-4 w-4 mr-2" />
                )}
                Connect Gmail
              </Button>
            </>
          )}
        </CardContent>
      </Card>

      {/* Future Integrations Placeholder */}
      <Card className="opacity-60">
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-blue-500/10">
              <Mail className="h-6 w-6 text-blue-500" />
            </div>
            <div>
              <CardTitle className="flex items-center gap-2">
                Google Calendar
                <Badge variant="outline">Coming Soon</Badge>
              </CardTitle>
              <CardDescription>
                Automatically add interview invites to your calendar
              </CardDescription>
            </div>
          </div>
        </CardHeader>
      </Card>
    </div>
  );
}
