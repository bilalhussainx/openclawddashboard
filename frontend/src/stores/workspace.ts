import { create } from 'zustand';

export interface Channel {
  id: number;
  channel_type: string;
  channel_type_display: string;
  name: string;
  allowlist: string[];
  is_active: boolean;
  respond_to_groups: boolean;
  created_at: string;
}

export interface InstalledSkill {
  id: number;
  skill: number;
  skill_name: string;
  skill_slug: string;
  is_enabled: boolean;
  config: object;
  installed_at: string;
}

export interface Workspace {
  id: number;
  name: string;
  description: string;
  selected_model: string;
  model_display: string;
  assigned_port: number | null;
  status: 'pending' | 'deploying' | 'running' | 'stopped' | 'error';
  status_display: string;
  is_running: boolean;
  last_health_check: string | null;
  error_message: string;
  sandbox_mode: boolean;
  max_tokens: number;
  channels: Channel[];
  installed_skills: InstalledSkill[];
  created_at: string;
  updated_at: string;
}

interface WorkspaceState {
  workspaces: Workspace[];
  currentWorkspace: Workspace | null;
  isLoading: boolean;
  error: string | null;

  setWorkspaces: (workspaces: Workspace[]) => void;
  addWorkspace: (workspace: Workspace) => void;
  updateWorkspace: (id: number, updates: Partial<Workspace>) => void;
  removeWorkspace: (id: number) => void;
  setCurrentWorkspace: (workspace: Workspace | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
}

export const useWorkspaceStore = create<WorkspaceState>((set) => ({
  workspaces: [],
  currentWorkspace: null,
  isLoading: false,
  error: null,

  setWorkspaces: (workspaces) => set({ workspaces }),

  addWorkspace: (workspace) =>
    set((state) => ({ workspaces: [...state.workspaces, workspace] })),

  updateWorkspace: (id, updates) =>
    set((state) => ({
      workspaces: state.workspaces.map((w) =>
        w.id === id ? { ...w, ...updates } : w
      ),
      currentWorkspace:
        state.currentWorkspace?.id === id
          ? { ...state.currentWorkspace, ...updates }
          : state.currentWorkspace,
    })),

  removeWorkspace: (id) =>
    set((state) => ({
      workspaces: state.workspaces.filter((w) => w.id !== id),
      currentWorkspace:
        state.currentWorkspace?.id === id ? null : state.currentWorkspace,
    })),

  setCurrentWorkspace: (workspace) => set({ currentWorkspace: workspace }),

  setLoading: (isLoading) => set({ isLoading }),

  setError: (error) => set({ error }),
}));
