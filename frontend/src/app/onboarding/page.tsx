'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { useToast } from '@/components/ui/use-toast';
import { useAuthStore } from '@/stores/auth';
import { authApi, workspaceApi, channelApi } from '@/lib/api';
import {
  ArrowRight,
  ArrowLeft,
  Check,
  Key,
  MessageSquare,
  Cpu,
  Rocket,
  Loader2,
} from 'lucide-react';
import { cn } from '@/lib/utils';

const steps = [
  { id: 'api-key', title: 'API Key', icon: Key },
  { id: 'model', title: 'Model', icon: Cpu },
  { id: 'channels', title: 'Channels', icon: MessageSquare, optional: true },
  { id: 'deploy', title: 'Deploy', icon: Rocket },
];

const models = [
  { id: 'claude-sonnet-4-20250514', name: 'Claude Sonnet 4', description: 'Best balance of speed and intelligence', recommended: true },
  { id: 'claude-opus-4-20250514', name: 'Claude Opus 4', description: 'Most capable for complex tasks' },
  { id: 'claude-3-5-haiku-20241022', name: 'Claude 3.5 Haiku', description: 'Fastest, most affordable' },
  { id: 'gpt-4-turbo-preview', name: 'GPT-4 Turbo', description: 'OpenAI\'s most capable model' },
];

const channels = [
  { id: 'telegram', name: 'Telegram', description: 'Bot token required', color: 'bg-blue-500' },
  { id: 'slack', name: 'Slack', description: 'OAuth connection', color: 'bg-purple-500' },
];

export default function OnboardingPage() {
  const [currentStep, setCurrentStep] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [apiKey, setApiKey] = useState('');
  const [apiKeyType, setApiKeyType] = useState<'anthropic' | 'openai'>('anthropic');
  const [selectedChannels, setSelectedChannels] = useState<string[]>([]);
  const [selectedModel, setSelectedModel] = useState('claude-sonnet-4-20250514');
  const [telegramToken, setTelegramToken] = useState('');
  const [workspaceName, setWorkspaceName] = useState('My Assistant');

  const router = useRouter();
  const { toast } = useToast();
  const { setUser } = useAuthStore();

  const handleNext = async () => {
    if (currentStep === 0) {
      // Save API key
      if (!apiKey) {
        toast({ variant: 'destructive', title: 'API key is required' });
        return;
      }
      setIsLoading(true);
      try {
        const keyData = apiKeyType === 'anthropic'
          ? { anthropic_api_key: apiKey }
          : { openai_api_key: apiKey };
        await authApi.updateApiKeys(keyData);
        const userResponse = await authApi.me();
        setUser(userResponse.data);
        setCurrentStep(1);
      } catch (error) {
        toast({ variant: 'destructive', title: 'Failed to save API key' });
      } finally {
        setIsLoading(false);
      }
    } else if (currentStep === 1) {
      // Model selected, move to channels (optional)
      setCurrentStep(2);
    } else if (currentStep === 2) {
      // Channels are optional, move to deploy
      setCurrentStep(3);
    }
  };

  const handleDeploy = async () => {
    setIsLoading(true);
    try {
      // Create workspace
      const workspaceResponse = await workspaceApi.create({
        name: workspaceName,
        selected_model: selectedModel,
      });
      const workspace = workspaceResponse.data;

      // Set up Telegram channel if selected
      if (selectedChannels.includes('telegram') && telegramToken) {
        await channelApi.setupTelegram(workspace.id, telegramToken);
      }

      // Deploy workspace
      await workspaceApi.deploy(workspace.id);

      toast({
        title: 'Deployment started!',
        description: 'Your AI assistant is being deployed.',
      });

      router.push(`/dashboard/workspaces/${workspace.id}`);
    } catch (error: any) {
      toast({
        variant: 'destructive',
        title: 'Deployment failed',
        description: error.response?.data?.error || 'Something went wrong',
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-muted/50 py-12 px-4">
      <div className="max-w-2xl mx-auto">
        {/* Progress Steps */}
        <div className="flex items-center justify-center mb-8">
          {steps.map((step, index) => (
            <div key={step.id} className="flex items-center">
              <div
                className={cn(
                  'flex items-center justify-center w-10 h-10 rounded-full border-2 transition-colors',
                  index < currentStep
                    ? 'bg-primary border-primary text-primary-foreground'
                    : index === currentStep
                    ? 'border-primary text-primary'
                    : 'border-muted-foreground/30 text-muted-foreground'
                )}
              >
                {index < currentStep ? (
                  <Check className="h-5 w-5" />
                ) : (
                  <step.icon className="h-5 w-5" />
                )}
              </div>
              {index < steps.length - 1 && (
                <div
                  className={cn(
                    'w-16 h-0.5 mx-2',
                    index < currentStep ? 'bg-primary' : 'bg-muted-foreground/30'
                  )}
                />
              )}
            </div>
          ))}
        </div>

        {/* Step Content */}
        <Card>
          {/* Step 1: API Key */}
          {currentStep === 0 && (
            <>
              <CardHeader>
                <CardTitle>Add your API Key</CardTitle>
                <CardDescription>
                  Connect your Anthropic or OpenAI account to power your assistant
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex space-x-2">
                  <Button
                    variant={apiKeyType === 'anthropic' ? 'default' : 'outline'}
                    onClick={() => setApiKeyType('anthropic')}
                    className="flex-1"
                  >
                    Anthropic (Claude)
                  </Button>
                  <Button
                    variant={apiKeyType === 'openai' ? 'default' : 'outline'}
                    onClick={() => setApiKeyType('openai')}
                    className="flex-1"
                  >
                    OpenAI (GPT)
                  </Button>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="apiKey">
                    {apiKeyType === 'anthropic' ? 'Anthropic' : 'OpenAI'} API Key
                  </Label>
                  <Input
                    id="apiKey"
                    type="password"
                    placeholder={apiKeyType === 'anthropic' ? 'sk-ant-...' : 'sk-...'}
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                  />
                  <p className="text-xs text-muted-foreground">
                    {apiKeyType === 'anthropic' ? (
                      <>Get your key from <a href="https://console.anthropic.com" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">console.anthropic.com</a></>
                    ) : (
                      <>Get your key from <a href="https://platform.openai.com" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">platform.openai.com</a></>
                    )}
                  </p>
                </div>
              </CardContent>
            </>
          )}

          {/* Step 2: Model */}
          {currentStep === 1 && (
            <>
              <CardHeader>
                <CardTitle>Select your model</CardTitle>
                <CardDescription>
                  Choose the AI model that powers your assistant
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {models.map((model) => (
                  <div
                    key={model.id}
                    onClick={() => setSelectedModel(model.id)}
                    className={cn(
                      'flex items-center justify-between p-4 rounded-lg border cursor-pointer transition-colors',
                      selectedModel === model.id
                        ? 'border-primary bg-primary/5'
                        : 'hover:bg-muted'
                    )}
                  >
                    <div>
                      <div className="flex items-center space-x-2">
                        <p className="font-medium">{model.name}</p>
                        {model.recommended && (
                          <span className="text-xs bg-primary/10 text-primary px-2 py-0.5 rounded">
                            Recommended
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-muted-foreground">{model.description}</p>
                    </div>
                    <div
                      className={cn(
                        'h-5 w-5 rounded-full border-2 flex items-center justify-center',
                        selectedModel === model.id
                          ? 'border-primary bg-primary'
                          : 'border-muted-foreground/30'
                      )}
                    >
                      {selectedModel === model.id && (
                        <Check className="h-3 w-3 text-primary-foreground" />
                      )}
                    </div>
                  </div>
                ))}
              </CardContent>
            </>
          )}

          {/* Step 3: Channels (Optional) */}
          {currentStep === 2 && (
            <>
              <CardHeader>
                <CardTitle>Connect channels (optional)</CardTitle>
                <CardDescription>
                  You can connect messaging platforms now or later from workspace settings
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-3">
                  {channels.map((channel) => (
                    <div
                      key={channel.id}
                      onClick={() => {
                        setSelectedChannels((prev) =>
                          prev.includes(channel.id)
                            ? prev.filter((c) => c !== channel.id)
                            : [...prev, channel.id]
                        );
                      }}
                      className={cn(
                        'flex items-center justify-between p-4 rounded-lg border cursor-pointer transition-colors',
                        selectedChannels.includes(channel.id)
                          ? 'border-primary bg-primary/5'
                          : 'hover:bg-muted'
                      )}
                    >
                      <div className="flex items-center space-x-3">
                        <div className={cn('h-10 w-10 rounded-lg flex items-center justify-center', channel.color)}>
                          <MessageSquare className="h-5 w-5 text-white" />
                        </div>
                        <div>
                          <p className="font-medium">{channel.name}</p>
                          <p className="text-sm text-muted-foreground">{channel.description}</p>
                        </div>
                      </div>
                      <div
                        className={cn(
                          'h-5 w-5 rounded border-2 flex items-center justify-center',
                          selectedChannels.includes(channel.id)
                            ? 'border-primary bg-primary'
                            : 'border-muted-foreground/30'
                        )}
                      >
                        {selectedChannels.includes(channel.id) && (
                          <Check className="h-3 w-3 text-primary-foreground" />
                        )}
                      </div>
                    </div>
                  ))}
                </div>

                {selectedChannels.includes('telegram') && (
                  <div className="space-y-2 p-4 rounded-lg border bg-muted/50">
                    <Label htmlFor="telegramToken">Telegram Bot Token</Label>
                    <Input
                      id="telegramToken"
                      type="password"
                      placeholder="123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
                      value={telegramToken}
                      onChange={(e) => setTelegramToken(e.target.value)}
                    />
                    <p className="text-xs text-muted-foreground">
                      Get your token from <a href="https://t.me/BotFather" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">@BotFather</a> on Telegram
                    </p>
                  </div>
                )}

                <p className="text-sm text-muted-foreground text-center">
                  You can skip this step and add channels later
                </p>
              </CardContent>
            </>
          )}

          {/* Step 4: Deploy */}
          {currentStep === 3 && (
            <>
              <CardHeader>
                <CardTitle>Ready to deploy!</CardTitle>
                <CardDescription>
                  Give your workspace a name and launch your assistant
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="workspaceName">Workspace Name</Label>
                  <Input
                    id="workspaceName"
                    value={workspaceName}
                    onChange={(e) => setWorkspaceName(e.target.value)}
                    placeholder="My AI Assistant"
                  />
                </div>

                <div className="rounded-lg bg-muted p-4 space-y-2">
                  <h4 className="font-medium">Summary</h4>
                  <div className="text-sm space-y-1">
                    <p><span className="text-muted-foreground">Model:</span> {models.find(m => m.id === selectedModel)?.name}</p>
                    <p><span className="text-muted-foreground">Channels:</span> {selectedChannels.length > 0 ? selectedChannels.join(', ') : 'None (can add later)'}</p>
                    <p><span className="text-muted-foreground">API:</span> {apiKeyType === 'anthropic' ? 'Anthropic' : 'OpenAI'}</p>
                  </div>
                </div>
              </CardContent>
            </>
          )}

          <CardFooter className="flex justify-between">
            <Button
              variant="outline"
              onClick={() => setCurrentStep((prev) => prev - 1)}
              disabled={currentStep === 0 || isLoading}
            >
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back
            </Button>

            {currentStep < 3 ? (
              <Button onClick={handleNext} disabled={isLoading}>
                {isLoading && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                Next
                <ArrowRight className="h-4 w-4 ml-2" />
              </Button>
            ) : (
              <Button onClick={handleDeploy} disabled={isLoading}>
                {isLoading && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                Deploy Assistant
                <Rocket className="h-4 w-4 ml-2" />
              </Button>
            )}
          </CardFooter>
        </Card>

        {/* Skip link */}
        <p className="text-center mt-4 text-sm text-muted-foreground">
          <button
            onClick={() => router.push('/dashboard')}
            className="hover:underline"
          >
            Skip for now and go to dashboard
          </button>
        </p>
      </div>
    </div>
  );
}
