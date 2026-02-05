'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  Book,
  MessageCircle,
  Github,
  ExternalLink,
  Mail,
  FileQuestion,
  Zap,
  Shield,
  Settings,
} from 'lucide-react';

const resources = [
  {
    title: 'Documentation',
    description: 'Learn how to use OpenClaw with comprehensive guides',
    icon: Book,
    href: 'https://docs.openclaw.ai',
  },
  {
    title: 'GitHub',
    description: 'View source code, report issues, and contribute',
    icon: Github,
    href: 'https://github.com/openclaw/openclaw',
  },
  {
    title: 'Discord Community',
    description: 'Join our community for help and discussions',
    icon: MessageCircle,
    href: 'https://discord.gg/openclaw',
  },
];

const faqs = [
  {
    question: 'How do I connect my Telegram bot?',
    answer: 'Create a bot with @BotFather on Telegram, copy the token, and add it in your workspace channel settings.',
  },
  {
    question: 'What AI models are supported?',
    answer: 'We support Claude (Opus, Sonnet, Haiku) from Anthropic and GPT-4/GPT-3.5 from OpenAI. Add your API key in Settings.',
  },
  {
    question: 'How is usage calculated?',
    answer: 'Usage is based on the number of messages processed and tokens used. View detailed analytics in the Analytics page.',
  },
  {
    question: 'Can I use my own OpenClaw instance?',
    answer: 'Yes! OpenClaw is open source. You can self-host or use our managed dashboard for easier deployment.',
  },
];

const guides = [
  {
    title: 'Getting Started',
    description: 'Set up your first AI assistant in minutes',
    icon: Zap,
  },
  {
    title: 'Security Best Practices',
    description: 'Keep your assistant and data secure',
    icon: Shield,
  },
  {
    title: 'Advanced Configuration',
    description: 'Customize your assistant behavior',
    icon: Settings,
  },
];

export default function HelpPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Help & Support</h1>
        <p className="text-muted-foreground">Get help with OpenClaw Dashboard</p>
      </div>

      {/* Quick Links */}
      <div className="grid gap-4 md:grid-cols-3">
        {resources.map((resource) => (
          <a
            key={resource.title}
            href={resource.href}
            target="_blank"
            rel="noopener noreferrer"
          >
            <Card className="hover:bg-muted/50 transition-colors cursor-pointer h-full">
              <CardHeader>
                <div className="flex items-center gap-3">
                  <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
                    <resource.icon className="h-5 w-5 text-primary" />
                  </div>
                  <div>
                    <CardTitle className="text-lg flex items-center gap-1">
                      {resource.title}
                      <ExternalLink className="h-3 w-3" />
                    </CardTitle>
                  </div>
                </div>
                <CardDescription>{resource.description}</CardDescription>
              </CardHeader>
            </Card>
          </a>
        ))}
      </div>

      {/* Quick Start Guides */}
      <Card>
        <CardHeader>
          <CardTitle>Quick Start Guides</CardTitle>
          <CardDescription>Learn the basics with these guides</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-3">
            {guides.map((guide) => (
              <div
                key={guide.title}
                className="flex items-start gap-3 p-4 rounded-lg border hover:bg-muted/50 cursor-pointer"
              >
                <guide.icon className="h-5 w-5 text-primary mt-0.5" />
                <div>
                  <p className="font-medium">{guide.title}</p>
                  <p className="text-sm text-muted-foreground">{guide.description}</p>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* FAQs */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileQuestion className="h-5 w-5" />
            Frequently Asked Questions
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {faqs.map((faq, i) => (
              <div key={i} className="p-4 rounded-lg border">
                <h4 className="font-medium mb-2">{faq.question}</h4>
                <p className="text-sm text-muted-foreground">{faq.answer}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Contact */}
      <Card>
        <CardHeader>
          <CardTitle>Still need help?</CardTitle>
          <CardDescription>We're here to assist you</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col sm:flex-row gap-4">
            <Button variant="outline" className="flex-1" asChild>
              <a href="mailto:support@openclaw.ai">
                <Mail className="h-4 w-4 mr-2" />
                Email Support
              </a>
            </Button>
            <Button variant="outline" className="flex-1" asChild>
              <a href="https://discord.gg/openclaw" target="_blank" rel="noopener noreferrer">
                <MessageCircle className="h-4 w-4 mr-2" />
                Join Discord
              </a>
            </Button>
            <Button variant="outline" className="flex-1" asChild>
              <a href="https://github.com/openclaw/openclaw/issues" target="_blank" rel="noopener noreferrer">
                <Github className="h-4 w-4 mr-2" />
                Report Issue
              </a>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
