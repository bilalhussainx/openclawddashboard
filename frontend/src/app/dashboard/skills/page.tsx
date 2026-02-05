'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { skillApi } from '@/lib/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Puzzle, Search, Star, Download, ExternalLink, Loader2 } from 'lucide-react';
import { InstallSkillDialog } from '@/components/skills/InstallSkillDialog';

interface Skill {
  id: number;
  name: string;
  slug: string;
  description: string;
  short_description: string;
  author: string;
  repository_url: string;
  icon_url: string;
  category: string;
  category_display: string;
  tags: string[];
  version: string;
  install_count: number;
  is_official: boolean;
  is_featured: boolean;
  average_rating: number | null;
  required_env?: string[];
}

export default function SkillsPage() {
  const [search, setSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [installDialogSkill, setInstallDialogSkill] = useState<Skill | null>(null);

  const { data: skills, isLoading } = useQuery<Skill[]>({
    queryKey: ['skills', search, selectedCategory],
    queryFn: async () => {
      const params: { search?: string; category?: string } = {};
      if (search) params.search = search;
      if (selectedCategory) params.category = selectedCategory;
      const response = await skillApi.list(params);
      return response.data.results || response.data;
    },
  });

  const { data: categories } = useQuery({
    queryKey: ['skill-categories'],
    queryFn: async () => {
      const response = await skillApi.categories();
      return response.data;
    },
  });

  const { data: featured } = useQuery<Skill[]>({
    queryKey: ['featured-skills'],
    queryFn: async () => {
      const response = await skillApi.featured();
      return response.data;
    },
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Skills Marketplace</h1>
        <p className="text-muted-foreground">Browse and install skills to extend your assistant's capabilities</p>
      </div>

      {/* Search and Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search skills..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <div className="flex gap-2 flex-wrap">
          <Button
            variant={selectedCategory === null ? 'default' : 'outline'}
            size="sm"
            onClick={() => setSelectedCategory(null)}
          >
            All
          </Button>
          {categories?.map((cat: { value: string; label: string; count: number }) => (
            <Button
              key={cat.value}
              variant={selectedCategory === cat.value ? 'default' : 'outline'}
              size="sm"
              onClick={() => setSelectedCategory(cat.value)}
            >
              {cat.label} ({cat.count})
            </Button>
          ))}
        </div>
      </div>

      {/* Featured Skills */}
      {!search && !selectedCategory && featured && featured.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold mb-4">Featured Skills</h2>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {featured.map((skill) => (
              <SkillCard key={skill.id} skill={skill} onInstall={setInstallDialogSkill} />
            ))}
          </div>
        </div>
      )}

      {/* All Skills */}
      <div>
        <h2 className="text-lg font-semibold mb-4">
          {search || selectedCategory ? 'Search Results' : 'All Skills'}
        </h2>
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : skills && skills.length > 0 ? (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {skills.map((skill) => (
              <SkillCard key={skill.id} skill={skill} onInstall={setInstallDialogSkill} />
            ))}
          </div>
        ) : (
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-12">
              <Puzzle className="h-12 w-12 text-muted-foreground mb-4" />
              <h3 className="font-medium mb-1">No skills found</h3>
              <p className="text-sm text-muted-foreground">
                {search ? 'Try a different search term' : 'No skills available in this category'}
              </p>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Install Dialog */}
      <InstallSkillDialog
        skill={installDialogSkill}
        open={!!installDialogSkill}
        onOpenChange={(open) => !open && setInstallDialogSkill(null)}
      />
    </div>
  );
}

function SkillCard({ skill, onInstall }: { skill: Skill; onInstall: (skill: Skill) => void }) {
  return (
    <Card className="hover:bg-muted/50 transition-colors">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
            <Puzzle className="h-5 w-5 text-primary" />
          </div>
          <div className="flex items-center gap-2">
            {skill.is_official && (
              <Badge variant="secondary">Official</Badge>
            )}
            {skill.is_featured && (
              <Badge>Featured</Badge>
            )}
          </div>
        </div>
        <CardTitle className="mt-3 text-lg">{skill.name}</CardTitle>
        <CardDescription>{skill.short_description || skill.description}</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="flex items-center justify-between text-sm text-muted-foreground mb-4">
          <span>by {skill.author}</span>
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1">
              <Download className="h-3 w-3" />
              {skill.install_count}
            </span>
            {skill.average_rating && (
              <span className="flex items-center gap-1">
                <Star className="h-3 w-3 fill-yellow-400 text-yellow-400" />
                {skill.average_rating.toFixed(1)}
              </span>
            )}
          </div>
        </div>
        <div className="flex gap-2">
          {skill.tags?.slice(0, 3).map((tag) => (
            <Badge key={tag} variant="outline" className="text-xs">
              {tag}
            </Badge>
          ))}
        </div>
        <div className="flex gap-2 mt-4">
          <Button size="sm" className="flex-1" onClick={() => onInstall(skill)}>
            Install
          </Button>
          {skill.repository_url && (
            <Button size="sm" variant="outline" asChild>
              <a href={skill.repository_url} target="_blank" rel="noopener noreferrer">
                <ExternalLink className="h-4 w-4" />
              </a>
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
