import Link from 'next/link';
import { Button } from '@/components/ui/button';
import {
  MessageSquare,
  Zap,
  Shield,
  Globe,
  ArrowRight,
  Check
} from 'lucide-react';

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-background to-muted">
      {/* Header */}
      <header className="container mx-auto px-4 py-6">
        <nav className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <div className="h-8 w-8 rounded-lg bg-primary flex items-center justify-center">
              <span className="text-primary-foreground font-bold">O</span>
            </div>
            <span className="font-bold text-xl">OpenClaw</span>
          </div>
          <div className="flex items-center space-x-4">
            <Link href="/login">
              <Button variant="ghost">Sign In</Button>
            </Link>
            <Link href="/register">
              <Button>Get Started</Button>
            </Link>
          </div>
        </nav>
      </header>

      {/* Hero Section */}
      <section className="container mx-auto px-4 py-20 text-center">
        <h1 className="text-5xl md:text-6xl font-bold tracking-tight mb-6">
          Deploy AI Assistants
          <br />
          <span className="text-primary">In 10 Minutes</span>
        </h1>
        <p className="text-xl text-muted-foreground max-w-2xl mx-auto mb-8">
          Connect your AI assistant to WhatsApp, Slack, Discord, and Teams.
          No code, no terminal, no DevOps required.
        </p>
        <div className="flex items-center justify-center space-x-4">
          <Link href="/register">
            <Button size="lg" className="text-lg px-8">
              Start Free
              <ArrowRight className="ml-2 h-5 w-5" />
            </Button>
          </Link>
          <Link href="https://github.com/openclaw/openclaw" target="_blank">
            <Button size="lg" variant="outline" className="text-lg px-8">
              View on GitHub
            </Button>
          </Link>
        </div>
      </section>

      {/* Channel Icons */}
      <section className="container mx-auto px-4 py-12">
        <div className="flex items-center justify-center space-x-8 opacity-60">
          <div className="text-center">
            <div className="h-12 w-12 mx-auto mb-2 rounded-lg bg-green-500/10 flex items-center justify-center">
              <MessageSquare className="h-6 w-6 text-green-500" />
            </div>
            <span className="text-sm">WhatsApp</span>
          </div>
          <div className="text-center">
            <div className="h-12 w-12 mx-auto mb-2 rounded-lg bg-purple-500/10 flex items-center justify-center">
              <MessageSquare className="h-6 w-6 text-purple-500" />
            </div>
            <span className="text-sm">Slack</span>
          </div>
          <div className="text-center">
            <div className="h-12 w-12 mx-auto mb-2 rounded-lg bg-indigo-500/10 flex items-center justify-center">
              <MessageSquare className="h-6 w-6 text-indigo-500" />
            </div>
            <span className="text-sm">Discord</span>
          </div>
          <div className="text-center">
            <div className="h-12 w-12 mx-auto mb-2 rounded-lg bg-blue-500/10 flex items-center justify-center">
              <MessageSquare className="h-6 w-6 text-blue-500" />
            </div>
            <span className="text-sm">Telegram</span>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="container mx-auto px-4 py-20">
        <h2 className="text-3xl font-bold text-center mb-12">
          Everything you need to deploy AI assistants
        </h2>
        <div className="grid md:grid-cols-3 gap-8">
          <div className="p-6 rounded-xl border bg-card">
            <div className="h-12 w-12 rounded-lg bg-primary/10 flex items-center justify-center mb-4">
              <Zap className="h-6 w-6 text-primary" />
            </div>
            <h3 className="text-xl font-semibold mb-2">Quick Setup</h3>
            <p className="text-muted-foreground">
              Visual onboarding wizard guides you through connecting your API keys
              and messaging channels in minutes.
            </p>
          </div>
          <div className="p-6 rounded-xl border bg-card">
            <div className="h-12 w-12 rounded-lg bg-primary/10 flex items-center justify-center mb-4">
              <Globe className="h-6 w-6 text-primary" />
            </div>
            <h3 className="text-xl font-semibold mb-2">Multi-Channel</h3>
            <p className="text-muted-foreground">
              Connect to WhatsApp, Telegram, Slack, Discord, and more.
              One assistant, all your channels.
            </p>
          </div>
          <div className="p-6 rounded-xl border bg-card">
            <div className="h-12 w-12 rounded-lg bg-primary/10 flex items-center justify-center mb-4">
              <Shield className="h-6 w-6 text-primary" />
            </div>
            <h3 className="text-xl font-semibold mb-2">Secure & Isolated</h3>
            <p className="text-muted-foreground">
              Each workspace runs in its own isolated container with
              sandbox mode for safe execution.
            </p>
          </div>
        </div>
      </section>

      {/* Pricing Preview */}
      <section className="container mx-auto px-4 py-20">
        <h2 className="text-3xl font-bold text-center mb-4">
          Simple, transparent pricing
        </h2>
        <p className="text-center text-muted-foreground mb-12">
          Start free, upgrade when you need more
        </p>
        <div className="grid md:grid-cols-3 gap-8 max-w-4xl mx-auto">
          <div className="p-6 rounded-xl border bg-card">
            <h3 className="text-lg font-semibold mb-2">Free</h3>
            <div className="text-3xl font-bold mb-4">$0</div>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li className="flex items-center">
                <Check className="h-4 w-4 mr-2 text-green-500" />
                1 channel (Telegram or Discord)
              </li>
              <li className="flex items-center">
                <Check className="h-4 w-4 mr-2 text-green-500" />
                1,000 messages/month
              </li>
              <li className="flex items-center">
                <Check className="h-4 w-4 mr-2 text-green-500" />
                Claude Haiku model
              </li>
            </ul>
          </div>
          <div className="p-6 rounded-xl border-2 border-primary bg-card relative">
            <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-primary text-primary-foreground text-xs px-3 py-1 rounded-full">
              Popular
            </div>
            <h3 className="text-lg font-semibold mb-2">Pro</h3>
            <div className="text-3xl font-bold mb-4">$49<span className="text-sm font-normal">/mo</span></div>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li className="flex items-center">
                <Check className="h-4 w-4 mr-2 text-green-500" />
                3 channels
              </li>
              <li className="flex items-center">
                <Check className="h-4 w-4 mr-2 text-green-500" />
                10,000 messages/month
              </li>
              <li className="flex items-center">
                <Check className="h-4 w-4 mr-2 text-green-500" />
                All Claude & GPT models
              </li>
            </ul>
          </div>
          <div className="p-6 rounded-xl border bg-card">
            <h3 className="text-lg font-semibold mb-2">Enterprise</h3>
            <div className="text-3xl font-bold mb-4">$199<span className="text-sm font-normal">/mo</span></div>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li className="flex items-center">
                <Check className="h-4 w-4 mr-2 text-green-500" />
                Unlimited channels
              </li>
              <li className="flex items-center">
                <Check className="h-4 w-4 mr-2 text-green-500" />
                100,000 messages/month
              </li>
              <li className="flex items-center">
                <Check className="h-4 w-4 mr-2 text-green-500" />
                White-label option
              </li>
            </ul>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="container mx-auto px-4 py-20 text-center">
        <h2 className="text-3xl font-bold mb-4">
          Ready to deploy your AI assistant?
        </h2>
        <p className="text-muted-foreground mb-8">
          Join hundreds of developers building with OpenClaw
        </p>
        <Link href="/register">
          <Button size="lg" className="text-lg px-8">
            Get Started for Free
            <ArrowRight className="ml-2 h-5 w-5" />
          </Button>
        </Link>
      </section>

      {/* Footer */}
      <footer className="border-t py-12">
        <div className="container mx-auto px-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <div className="h-6 w-6 rounded bg-primary flex items-center justify-center">
                <span className="text-primary-foreground font-bold text-xs">O</span>
              </div>
              <span className="font-semibold">OpenClaw Dashboard</span>
            </div>
            <div className="flex items-center space-x-6 text-sm text-muted-foreground">
              <Link href="https://docs.openclaw.ai" className="hover:text-foreground">
                Docs
              </Link>
              <Link href="https://github.com/openclaw/openclaw" className="hover:text-foreground">
                GitHub
              </Link>
              <Link href="https://discord.gg/openclaw" className="hover:text-foreground">
                Discord
              </Link>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
