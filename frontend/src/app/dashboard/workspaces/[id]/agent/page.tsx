'use client';

import { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { workspaceApi, knowledgeApi } from '@/lib/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { useToast } from '@/components/ui/use-toast';
import {
  ArrowLeft,
  Bot,
  Brain,
  MessageSquare,
  FileText,
  Plus,
  Trash2,
  Send,
  Loader2,
  Save,
  Sparkles,
  HelpCircle,
} from 'lucide-react';
import Link from 'next/link';

const modelOptions = [
  { id: 'claude-sonnet-4-20250514', name: 'Claude Sonnet 4', provider: 'Anthropic' },
  { id: 'claude-opus-4-20250514', name: 'Claude Opus 4', provider: 'Anthropic' },
  { id: 'claude-3-5-haiku-20241022', name: 'Claude 3.5 Haiku', provider: 'Anthropic' },
  { id: 'gpt-4-turbo-preview', name: 'GPT-4 Turbo', provider: 'OpenAI' },
];

const promptTemplates = [
  {
    name: 'Customer Support',
    prompt: `You are a helpful customer support agent. Your goals are:
- Answer customer questions accurately and professionally
- Help resolve issues efficiently
- Escalate complex problems when necessary
- Always maintain a friendly, empathetic tone

If you don't know something, admit it and offer to find the answer.`,
  },
  {
    name: 'Personal Assistant',
    prompt: `You are a personal AI assistant. You help with:
- Answering questions and providing information
- Helping organize tasks and ideas
- Providing thoughtful advice
- Engaging in friendly conversation

Be conversational, helpful, and adapt to the user's communication style.`,
  },
  {
    name: 'Technical Expert',
    prompt: `You are a technical expert assistant. You:
- Provide accurate technical information
- Explain complex concepts clearly
- Help debug and solve problems
- Suggest best practices and solutions

Use code examples when helpful. Ask clarifying questions when needed.`,
  },
];

export default function AgentConfigPage() {
  const params = useParams();
  const router = useRouter();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const workspaceId = Number(params.id);

  const [activeTab, setActiveTab] = useState<'config' | 'knowledge' | 'test'>('config');
  const [testMessage, setTestMessage] = useState('');
  const [testResponse, setTestResponse] = useState('');
  const [isTesting, setIsTesting] = useState(false);

  // Form state
  const [formData, setFormData] = useState({
    system_prompt: '',
    agent_name: 'Assistant',
    agent_description: '',
    welcome_message: 'Hello! How can I help you today?',
    temperature: 0.7,
    selected_model: 'claude-sonnet-4-20250514',
    max_tokens: 4096,
  });

  // New knowledge entry form
  const [newEntry, setNewEntry] = useState({
    name: '',
    resource_type: 'text',
    content: '',
    question: '',
    answer: '',
  });

  // Fetch workspace data
  const { data: workspace, isLoading } = useQuery({
    queryKey: ['workspace', workspaceId],
    queryFn: async () => {
      const response = await workspaceApi.get(workspaceId);
      const data = response.data;
      setFormData({
        system_prompt: data.system_prompt || '',
        agent_name: data.agent_name || 'Assistant',
        agent_description: data.agent_description || '',
        welcome_message: data.welcome_message || 'Hello! How can I help you today?',
        temperature: data.temperature || 0.7,
        selected_model: data.selected_model || 'claude-sonnet-4-20250514',
        max_tokens: data.max_tokens || 4096,
      });
      return data;
    },
  });

  // Fetch knowledge base
  const { data: knowledge } = useQuery({
    queryKey: ['knowledge', workspaceId],
    queryFn: async () => {
      const response = await knowledgeApi.list(workspaceId);
      return response.data.results || response.data;
    },
  });

  // Save agent config mutation
  const saveConfig = useMutation({
    mutationFn: (data: typeof formData) => workspaceApi.updateAgentConfig(workspaceId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workspace', workspaceId] });
      toast({ title: 'Agent configuration saved!' });
    },
    onError: () => {
      toast({ variant: 'destructive', title: 'Failed to save configuration' });
    },
  });

  // Add knowledge entry mutation
  const addKnowledge = useMutation({
    mutationFn: (data: typeof newEntry) => knowledgeApi.create(workspaceId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['knowledge', workspaceId] });
      setNewEntry({ name: '', resource_type: 'text', content: '', question: '', answer: '' });
      toast({ title: 'Knowledge entry added!' });
    },
    onError: () => {
      toast({ variant: 'destructive', title: 'Failed to add knowledge entry' });
    },
  });

  // Delete knowledge entry mutation
  const deleteKnowledge = useMutation({
    mutationFn: (id: number) => knowledgeApi.delete(workspaceId, id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['knowledge', workspaceId] });
      toast({ title: 'Knowledge entry deleted' });
    },
  });

  // Test message
  const handleTestMessage = async () => {
    if (!testMessage.trim()) return;

    setIsTesting(true);
    setTestResponse('');

    try {
      const response = await workspaceApi.testMessage(workspaceId, testMessage);
      setTestResponse(response.data.reply);
    } catch (error: any) {
      setTestResponse(`Error: ${error.response?.data?.error || 'Failed to get response'}`);
    } finally {
      setIsTesting(false);
    }
  };

  const applyTemplate = (template: typeof promptTemplates[0]) => {
    setFormData((prev) => ({ ...prev, system_prompt: template.prompt }));
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href={`/dashboard/workspaces/${workspaceId}`}>
            <Button variant="ghost" size="icon">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2">
              <Bot className="h-6 w-6" />
              Configure Agent
            </h1>
            <p className="text-muted-foreground">{workspace?.name}</p>
          </div>
        </div>
        <Button onClick={() => saveConfig.mutate(formData)} disabled={saveConfig.isPending}>
          {saveConfig.isPending ? (
            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
          ) : (
            <Save className="h-4 w-4 mr-2" />
          )}
          Save Configuration
        </Button>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b">
        <button
          onClick={() => setActiveTab('config')}
          className={`px-4 py-2 border-b-2 transition-colors ${
            activeTab === 'config'
              ? 'border-primary text-primary'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          <Brain className="h-4 w-4 inline mr-2" />
          Behavior
        </button>
        <button
          onClick={() => setActiveTab('knowledge')}
          className={`px-4 py-2 border-b-2 transition-colors ${
            activeTab === 'knowledge'
              ? 'border-primary text-primary'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          <FileText className="h-4 w-4 inline mr-2" />
          Knowledge Base
        </button>
        <button
          onClick={() => setActiveTab('test')}
          className={`px-4 py-2 border-b-2 transition-colors ${
            activeTab === 'test'
              ? 'border-primary text-primary'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          <MessageSquare className="h-4 w-4 inline mr-2" />
          Test Agent
        </button>
      </div>

      {/* Config Tab */}
      {activeTab === 'config' && (
        <div className="grid gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2 space-y-6">
            {/* System Prompt */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Sparkles className="h-5 w-5" />
                  System Prompt
                </CardTitle>
                <CardDescription>
                  Define your agent's personality, role, and behavior
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex gap-2 flex-wrap">
                  <span className="text-sm text-muted-foreground">Templates:</span>
                  {promptTemplates.map((template) => (
                    <Button
                      key={template.name}
                      variant="outline"
                      size="sm"
                      onClick={() => applyTemplate(template)}
                    >
                      {template.name}
                    </Button>
                  ))}
                </div>
                <textarea
                  className="w-full min-h-[200px] p-3 rounded-lg border bg-background resize-y"
                  placeholder="You are a helpful AI assistant..."
                  value={formData.system_prompt}
                  onChange={(e) => setFormData((prev) => ({ ...prev, system_prompt: e.target.value }))}
                />
                <p className="text-xs text-muted-foreground">
                  Tip: Be specific about the agent's role, tone, and any limitations.
                </p>
              </CardContent>
            </Card>

            {/* Welcome Message */}
            <Card>
              <CardHeader>
                <CardTitle>Welcome Message</CardTitle>
                <CardDescription>
                  First message sent when a user starts a conversation
                </CardDescription>
              </CardHeader>
              <CardContent>
                <textarea
                  className="w-full min-h-[80px] p-3 rounded-lg border bg-background resize-y"
                  placeholder="Hello! How can I help you today?"
                  value={formData.welcome_message}
                  onChange={(e) => setFormData((prev) => ({ ...prev, welcome_message: e.target.value }))}
                />
              </CardContent>
            </Card>
          </div>

          {/* Settings Sidebar */}
          <div className="space-y-6">
            {/* Agent Identity */}
            <Card>
              <CardHeader>
                <CardTitle>Agent Identity</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="agent_name">Name</Label>
                  <Input
                    id="agent_name"
                    value={formData.agent_name}
                    onChange={(e) => setFormData((prev) => ({ ...prev, agent_name: e.target.value }))}
                    placeholder="Assistant"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="agent_description">Description</Label>
                  <Input
                    id="agent_description"
                    value={formData.agent_description}
                    onChange={(e) => setFormData((prev) => ({ ...prev, agent_description: e.target.value }))}
                    placeholder="A helpful AI assistant"
                  />
                </div>
              </CardContent>
            </Card>

            {/* Model Settings */}
            <Card>
              <CardHeader>
                <CardTitle>Model Settings</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label>Model</Label>
                  <select
                    className="w-full p-2 rounded-lg border bg-background"
                    value={formData.selected_model}
                    onChange={(e) => setFormData((prev) => ({ ...prev, selected_model: e.target.value }))}
                  >
                    {modelOptions.map((model) => (
                      <option key={model.id} value={model.id}>
                        {model.name} ({model.provider})
                      </option>
                    ))}
                  </select>
                </div>

                <div className="space-y-2">
                  <Label>Temperature: {formData.temperature}</Label>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.1"
                    className="w-full"
                    value={formData.temperature}
                    onChange={(e) => setFormData((prev) => ({ ...prev, temperature: parseFloat(e.target.value) }))}
                  />
                  <div className="flex justify-between text-xs text-muted-foreground">
                    <span>Precise</span>
                    <span>Creative</span>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="max_tokens">Max Tokens</Label>
                  <Input
                    id="max_tokens"
                    type="number"
                    value={formData.max_tokens}
                    onChange={(e) => setFormData((prev) => ({ ...prev, max_tokens: parseInt(e.target.value) }))}
                  />
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      )}

      {/* Knowledge Base Tab */}
      {activeTab === 'knowledge' && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Plus className="h-5 w-5" />
                Add Knowledge
              </CardTitle>
              <CardDescription>
                Add information the agent can reference when answering questions
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label>Name</Label>
                  <Input
                    placeholder="Product FAQ, Company Info, etc."
                    value={newEntry.name}
                    onChange={(e) => setNewEntry((prev) => ({ ...prev, name: e.target.value }))}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Type</Label>
                  <select
                    className="w-full p-2 rounded-lg border bg-background"
                    value={newEntry.resource_type}
                    onChange={(e) => setNewEntry((prev) => ({ ...prev, resource_type: e.target.value }))}
                  >
                    <option value="text">Text Snippet</option>
                    <option value="faq">FAQ Entry</option>
                  </select>
                </div>
              </div>

              {newEntry.resource_type === 'text' && (
                <div className="space-y-2">
                  <Label>Content</Label>
                  <textarea
                    className="w-full min-h-[100px] p-3 rounded-lg border bg-background resize-y"
                    placeholder="Enter the information you want the agent to know..."
                    value={newEntry.content}
                    onChange={(e) => setNewEntry((prev) => ({ ...prev, content: e.target.value }))}
                  />
                </div>
              )}

              {newEntry.resource_type === 'faq' && (
                <>
                  <div className="space-y-2">
                    <Label>Question</Label>
                    <Input
                      placeholder="What question does this answer?"
                      value={newEntry.question}
                      onChange={(e) => setNewEntry((prev) => ({ ...prev, question: e.target.value }))}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Answer</Label>
                    <textarea
                      className="w-full min-h-[80px] p-3 rounded-lg border bg-background resize-y"
                      placeholder="The answer to the question..."
                      value={newEntry.answer}
                      onChange={(e) => setNewEntry((prev) => ({ ...prev, answer: e.target.value }))}
                    />
                  </div>
                </>
              )}

              <Button
                onClick={() => addKnowledge.mutate(newEntry)}
                disabled={addKnowledge.isPending || !newEntry.name}
              >
                {addKnowledge.isPending ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <Plus className="h-4 w-4 mr-2" />
                )}
                Add Entry
              </Button>
            </CardContent>
          </Card>

          {/* Knowledge Entries */}
          <Card>
            <CardHeader>
              <CardTitle>Knowledge Entries</CardTitle>
              <CardDescription>
                {knowledge?.length || 0} entries in the knowledge base
              </CardDescription>
            </CardHeader>
            <CardContent>
              {knowledge && knowledge.length > 0 ? (
                <div className="space-y-3">
                  {knowledge.map((entry: any) => (
                    <div
                      key={entry.id}
                      className="flex items-start justify-between p-4 rounded-lg border"
                    >
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <p className="font-medium">{entry.name}</p>
                          <Badge variant="secondary">{entry.resource_type_display}</Badge>
                        </div>
                        {entry.resource_type === 'faq' ? (
                          <div className="text-sm text-muted-foreground">
                            <p><strong>Q:</strong> {entry.question}</p>
                            <p><strong>A:</strong> {entry.answer?.substring(0, 100)}...</p>
                          </div>
                        ) : (
                          <p className="text-sm text-muted-foreground">
                            {entry.content?.substring(0, 150)}...
                          </p>
                        )}
                      </div>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => deleteKnowledge.mutate(entry.id)}
                      >
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center py-8 text-center">
                  <HelpCircle className="h-12 w-12 text-muted-foreground mb-4" />
                  <h3 className="font-medium mb-1">No knowledge entries yet</h3>
                  <p className="text-sm text-muted-foreground">
                    Add FAQs, product info, or other content the agent should know
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* Test Tab */}
      {activeTab === 'test' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <MessageSquare className="h-5 w-5" />
              Test Your Agent
            </CardTitle>
            <CardDescription>
              Send a test message to see how your agent responds
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="p-4 rounded-lg border bg-muted/50 min-h-[200px]">
              {testResponse ? (
                <div className="space-y-4">
                  <div className="flex justify-end">
                    <div className="bg-primary text-primary-foreground rounded-lg px-4 py-2 max-w-[80%]">
                      {testMessage}
                    </div>
                  </div>
                  <div className="flex justify-start">
                    <div className="bg-background border rounded-lg px-4 py-2 max-w-[80%]">
                      {testResponse}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
                  <MessageSquare className="h-8 w-8 mb-2" />
                  <p>Send a message to test your agent</p>
                </div>
              )}
            </div>

            <div className="flex gap-2">
              <Input
                placeholder="Type a test message..."
                value={testMessage}
                onChange={(e) => setTestMessage(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleTestMessage()}
              />
              <Button onClick={handleTestMessage} disabled={isTesting || !testMessage.trim()}>
                {isTesting ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
              </Button>
            </div>

            <p className="text-xs text-muted-foreground">
              Note: This uses your API key to send a real request. Make sure to save your configuration first.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
