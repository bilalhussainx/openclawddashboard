'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '@/stores/auth';
import { authApi } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { useToast } from '@/components/ui/use-toast';
import { Loader2, Key, User, Lock, Puzzle, ExternalLink, Check } from 'lucide-react';

const profileSchema = z.object({
  first_name: z.string().optional(),
  last_name: z.string().optional(),
  company_name: z.string().optional(),
});

const apiKeySchema = z.object({
  anthropic_api_key: z.string().optional(),
  openai_api_key: z.string().optional(),
});

const passwordSchema = z.object({
  old_password: z.string().min(1, 'Current password is required'),
  new_password: z.string().min(6, 'Password must be at least 6 characters'),
  new_password_confirm: z.string(),
}).refine((data) => data.new_password === data.new_password_confirm, {
  message: 'Passwords do not match',
  path: ['new_password_confirm'],
});

interface SkillApiKeyInfo {
  key: string;
  name: string;
  description: string;
  url: string;
  is_configured: boolean;
}

export default function SettingsPage() {
  const { user, setUser } = useAuthStore();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [isProfileLoading, setIsProfileLoading] = useState(false);
  const [isApiKeyLoading, setIsApiKeyLoading] = useState(false);
  const [isPasswordLoading, setIsPasswordLoading] = useState(false);
  const [skillKeyInputs, setSkillKeyInputs] = useState<Record<string, string>>({});

  const profileForm = useForm({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      first_name: user?.first_name || '',
      last_name: user?.last_name || '',
      company_name: user?.company_name || '',
    },
  });

  const apiKeyForm = useForm({
    resolver: zodResolver(apiKeySchema),
    defaultValues: {
      anthropic_api_key: '',
      openai_api_key: '',
    },
  });

  const passwordForm = useForm({
    resolver: zodResolver(passwordSchema),
    defaultValues: {
      old_password: '',
      new_password: '',
      new_password_confirm: '',
    },
  });

  const { data: skillApiKeys, isLoading: isSkillKeysLoading } = useQuery<{ keys: SkillApiKeyInfo[]; configured_count: number }>({
    queryKey: ['skill-api-keys'],
    queryFn: async () => {
      const response = await authApi.getSkillApiKeys();
      return response.data;
    },
  });

  const updateSkillKeysMutation = useMutation({
    mutationFn: async (keys: Record<string, string | null>) => {
      console.log('Saving skill API keys:', keys);
      const response = await authApi.updateSkillApiKeys(keys);
      console.log('Save response:', response.data);
      return response;
    },
    onSuccess: (response) => {
      console.log('Skill API keys saved successfully:', response.data);
      toast({ title: 'Skill API keys updated' });
      queryClient.invalidateQueries({ queryKey: ['skill-api-keys'] });
      setSkillKeyInputs({});
    },
    onError: (error: any) => {
      console.error('Failed to save skill API keys:', error);
      toast({
        variant: 'destructive',
        title: 'Failed to update skill API keys',
        description: error.response?.data?.error || 'Something went wrong',
      });
    },
  });

  const onProfileSubmit = async (data: z.infer<typeof profileSchema>) => {
    setIsProfileLoading(true);
    try {
      const response = await authApi.updateProfile(data);
      setUser(response.data);
      toast({ title: 'Profile updated successfully' });
    } catch (error: any) {
      toast({
        variant: 'destructive',
        title: 'Failed to update profile',
        description: error.response?.data?.detail || 'Something went wrong',
      });
    } finally {
      setIsProfileLoading(false);
    }
  };

  const onApiKeySubmit = async (data: z.infer<typeof apiKeySchema>) => {
    setIsApiKeyLoading(true);
    try {
      await authApi.updateApiKeys(data);
      const userResponse = await authApi.me();
      setUser(userResponse.data);
      apiKeyForm.reset();
      toast({ title: 'API keys updated successfully' });
    } catch (error: any) {
      toast({
        variant: 'destructive',
        title: 'Failed to update API keys',
        description: error.response?.data?.detail || 'Something went wrong',
      });
    } finally {
      setIsApiKeyLoading(false);
    }
  };

  const onPasswordSubmit = async (data: z.infer<typeof passwordSchema>) => {
    setIsPasswordLoading(true);
    try {
      await authApi.changePassword(data);
      passwordForm.reset();
      toast({ title: 'Password changed successfully' });
    } catch (error: any) {
      toast({
        variant: 'destructive',
        title: 'Failed to change password',
        description: error.response?.data?.old_password?.[0] || error.response?.data?.detail || 'Something went wrong',
      });
    } finally {
      setIsPasswordLoading(false);
    }
  };

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Settings</h1>
        <p className="text-muted-foreground">Manage your account settings and API keys</p>
      </div>

      {/* Profile Settings */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <User className="h-5 w-5" />
            Profile
          </CardTitle>
          <CardDescription>Update your personal information</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={profileForm.handleSubmit(onProfileSubmit)} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="first_name">First Name</Label>
                <Input id="first_name" {...profileForm.register('first_name')} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="last_name">Last Name</Label>
                <Input id="last_name" {...profileForm.register('last_name')} />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="company_name">Company Name</Label>
              <Input id="company_name" {...profileForm.register('company_name')} />
            </div>
            <div className="space-y-2">
              <Label>Email</Label>
              <Input value={user?.email || ''} disabled />
              <p className="text-xs text-muted-foreground">Email cannot be changed</p>
            </div>
            <Button type="submit" disabled={isProfileLoading}>
              {isProfileLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Save Profile
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* API Keys */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Key className="h-5 w-5" />
            API Keys
          </CardTitle>
          <CardDescription>
            Configure your AI provider API keys. Keys are stored securely.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={apiKeyForm.handleSubmit(onApiKeySubmit)} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="anthropic_api_key">
                Anthropic API Key
                {user?.has_anthropic_key && (
                  <span className="ml-2 text-xs text-green-600">(configured)</span>
                )}
              </Label>
              <Input
                id="anthropic_api_key"
                type="password"
                placeholder={user?.has_anthropic_key ? '••••••••••••••••' : 'sk-ant-...'}
                {...apiKeyForm.register('anthropic_api_key')}
              />
              <p className="text-xs text-muted-foreground">
                Get your key from{' '}
                <a href="https://console.anthropic.com" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">
                  console.anthropic.com
                </a>
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="openai_api_key">
                OpenAI API Key
                {user?.has_openai_key && (
                  <span className="ml-2 text-xs text-green-600">(configured)</span>
                )}
              </Label>
              <Input
                id="openai_api_key"
                type="password"
                placeholder={user?.has_openai_key ? '••••••••••••••••' : 'sk-...'}
                {...apiKeyForm.register('openai_api_key')}
              />
              <p className="text-xs text-muted-foreground">
                Get your key from{' '}
                <a href="https://platform.openai.com" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">
                  platform.openai.com
                </a>
              </p>
            </div>
            <Button type="submit" disabled={isApiKeyLoading}>
              {isApiKeyLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Update API Keys
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Change Password */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Lock className="h-5 w-5" />
            Change Password
          </CardTitle>
          <CardDescription>Update your account password</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={passwordForm.handleSubmit(onPasswordSubmit)} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="old_password">Current Password</Label>
              <Input id="old_password" type="password" {...passwordForm.register('old_password')} />
              {passwordForm.formState.errors.old_password && (
                <p className="text-sm text-destructive">{passwordForm.formState.errors.old_password.message}</p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="new_password">New Password</Label>
              <Input id="new_password" type="password" {...passwordForm.register('new_password')} />
              {passwordForm.formState.errors.new_password && (
                <p className="text-sm text-destructive">{passwordForm.formState.errors.new_password.message}</p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="new_password_confirm">Confirm New Password</Label>
              <Input id="new_password_confirm" type="password" {...passwordForm.register('new_password_confirm')} />
              {passwordForm.formState.errors.new_password_confirm && (
                <p className="text-sm text-destructive">{passwordForm.formState.errors.new_password_confirm.message}</p>
              )}
            </div>
            <Button type="submit" disabled={isPasswordLoading}>
              {isPasswordLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Change Password
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Skill API Keys */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Puzzle className="h-5 w-5" />
            Skill API Keys
          </CardTitle>
          <CardDescription>
            Configure API keys required by skills like web search, GitHub integration, etc.
            {skillApiKeys && (
              <span className="ml-2 text-xs">
                ({skillApiKeys.configured_count} of {skillApiKeys.keys.length} configured)
              </span>
            )}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isSkillKeysLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : (
            <div className="space-y-4">
              {skillApiKeys?.keys.map((keyInfo) => (
                <div key={keyInfo.key} className="space-y-2">
                  <div className="flex items-center justify-between">
                    <Label htmlFor={keyInfo.key} className="flex items-center gap-2">
                      {keyInfo.name}
                      {keyInfo.is_configured && (
                        <span className="flex items-center text-xs text-green-600">
                          <Check className="h-3 w-3 mr-1" />
                          configured
                        </span>
                      )}
                    </Label>
                    <a
                      href={keyInfo.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-primary hover:underline flex items-center gap-1"
                    >
                      Get key
                      <ExternalLink className="h-3 w-3" />
                    </a>
                  </div>
                  <Input
                    id={keyInfo.key}
                    type="password"
                    placeholder={keyInfo.is_configured ? '••••••••••••••••' : `Enter ${keyInfo.name}`}
                    value={skillKeyInputs[keyInfo.key] || ''}
                    onChange={(e) => {
                      const newValue = e.target.value;
                      console.log(`Input changed for ${keyInfo.key}:`, newValue ? `${newValue.substring(0, 4)}...` : '(empty)');
                      setSkillKeyInputs((prev) => ({
                        ...prev,
                        [keyInfo.key]: newValue,
                      }));
                    }}
                  />
                  <p className="text-xs text-muted-foreground">{keyInfo.description}</p>
                </div>
              ))}
              <Button
                onClick={() => {
                  console.log('Save button clicked, skillKeyInputs:', skillKeyInputs);
                  console.log('Keys to save:', Object.keys(skillKeyInputs));
                  updateSkillKeysMutation.mutate(skillKeyInputs);
                }}
                disabled={
                  updateSkillKeysMutation.isPending ||
                  Object.keys(skillKeyInputs).length === 0
                }
              >
                {updateSkillKeysMutation.isPending && (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                )}
                Save Skill API Keys
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
