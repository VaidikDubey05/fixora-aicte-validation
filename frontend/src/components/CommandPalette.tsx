import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Search,
  FileText,
  ShieldCheck,
  ShieldAlert,
  Sparkles,
  Bell,
  Sun,
  Moon,
  Keyboard,
  ArrowRight,
  UserCheck,
  Layers,
  Building2,
  CheckCircle2,
} from 'lucide-react';
import { useTheme } from '../context/ThemeContext';
import { useAuth } from '../context/AuthContext';
import { DEMO_USERS } from '../lib/mockFallback';

interface CommandItem {
  id: string;
  title: string;
  description: string;
  category: 'Navigation' | 'Statutory Dossiers' | 'Quick Actions' | 'Switch Persona';
  icon: any;
  shortcut?: string;
  action: () => void;
}

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
  onOpenAssistant: () => void;
  onOpenAlerts: () => void;
  onOpenShortcuts: () => void;
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({
  isOpen,
  onClose,
  onOpenAssistant,
  onOpenAlerts,
  onOpenShortcuts,
}) => {
  const [query, setQuery] = useState<string>('');
  const [selectedIndex, setSelectedIndex] = useState<number>(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();
  const { theme, toggleTheme } = useTheme();
  const { login: setAuthSession } = useAuth();

  useEffect(() => {
    if (isOpen) {
      setQuery('');
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  const switchPersona = (email: string) => {
    const user = DEMO_USERS[email];
    if (user) {
      setAuthSession(`mock_jwt_token_${user.role}`, user);
      onClose();
      if (user.role === 'institution') navigate('/institution/dashboard');
      else if (user.role === 'scrutiny_officer') navigate('/officer/overview');
      else if (user.role === 'verification_officer') navigate('/officer/verification');
      else navigate('/admin/analytics');
    }
  };

  const allCommands: CommandItem[] = [
    // Navigation
    {
      id: 'nav-landing',
      title: 'Platform Overview & 3D Hero Landing Page',
      description: 'Explore the 7-stage autonomous pipeline & interactive 3D document scanner',
      category: 'Navigation',
      icon: Sparkles,
      action: () => {
        navigate('/');
        onClose();
      },
    },
    {
      id: 'nav-scrutiny-overview',
      title: 'Scrutiny Officer Overview',
      description: 'KPI metrics, priority queue & intake deficiency distribution',
      category: 'Navigation',
      icon: ShieldCheck,
      action: () => {
        navigate('/officer/overview');
        onClose();
      },
    },
    {
      id: 'nav-app-queue',
      title: 'Applications Scrutiny Queue',
      description: 'Server-side filterable list of institutional dossiers',
      category: 'Navigation',
      icon: Layers,
      action: () => {
        navigate('/officer/applications');
        onClose();
      },
    },
    {
      id: 'nav-verification-bureau',
      title: 'State & Central Registry Verification Queue',
      description: 'Land records, fire NOCs, and municipal certificates gateway',
      category: 'Navigation',
      icon: CheckCircle2,
      action: () => {
        navigate('/officer/verification');
        onClose();
      },
    },
    {
      id: 'nav-inspection-queue',
      title: 'On-site Inspection Queue',
      description: 'Schedule and track physical campus committee inspections',
      category: 'Navigation',
      icon: Building2,
      action: () => {
        navigate('/officer/inspection');
        onClose();
      },
    },
    {
      id: 'nav-rule-packs',
      title: 'Rule Packs Governance (Maker-Checker)',
      description: 'Edit YAML compliance rules, version diff & dual authorization',
      category: 'Navigation',
      icon: FileText,
      action: () => {
        navigate('/admin/rules');
        onClose();
      },
    },
    {
      id: 'nav-audit-explorer',
      title: 'Cryptographic Audit Chain Ledger',
      description: 'Inspect SHA-256 tamper-evident regulatory timeline',
      category: 'Navigation',
      icon: ShieldAlert,
      action: () => {
        navigate('/admin/audit');
        onClose();
      },
    },
    {
      id: 'nav-admin-analytics',
      title: 'Statutory Benchmark Analytics',
      description: 'Deficiency metrics from synthetic benchmark eval suite',
      category: 'Navigation',
      icon: Layers,
      action: () => {
        navigate('/admin/analytics');
        onClose();
      },
    },
    {
      id: 'nav-institution-dash',
      title: 'Institution Dossier Dashboard',
      description: 'Track application states, upload documents & view findings',
      category: 'Navigation',
      icon: Building2,
      action: () => {
        navigate('/institution/dashboard');
        onClose();
      },
    },
    {
      id: 'nav-new-application',
      title: 'New Application Submission Wizard',
      description: '4-step wizard with real-time 7-stage validation pipeline',
      category: 'Navigation',
      icon: FileText,
      action: () => {
        navigate('/institution/applications/new');
        onClose();
      },
    },

    // Statutory Dossiers
    {
      id: 'dossier-gec-pune',
      title: 'APP-EOA-2024-00001: Government College of Engineering, Pune',
      description: 'Review Workspace: Fire NOC lapsed & Built-up area mismatch',
      category: 'Statutory Dossiers',
      icon: FileText,
      action: () => {
        navigate('/officer/applications/APP-EOA-2024-00001');
        onClose();
      },
    },
    {
      id: 'dossier-delhi-tech',
      title: 'APP-EOA-2024-00002: Delhi Institute of Applied Technology',
      description: 'Priority score 94, 3 deficiencies queued for rectification',
      category: 'Statutory Dossiers',
      icon: FileText,
      action: () => {
        navigate('/officer/applications/APP-EOA-2024-00002');
        onClose();
      },
    },
    {
      id: 'dossier-chennai-pharmacy',
      title: 'APP-EOA-2024-00004: Chennai College of Pharmacy',
      description: 'Rectified building compliance certificate pending review',
      category: 'Statutory Dossiers',
      icon: FileText,
      action: () => {
        navigate('/officer/applications/APP-EOA-2024-00004');
        onClose();
      },
    },

    // Quick Actions
    {
      id: 'action-ask-fixora',
      title: 'Ask FIXORA Statutory Copilot',
      description: 'AICTE Approval Process Handbook (APH 2026-27) QA Assistant',
      category: 'Quick Actions',
      icon: Sparkles,
      shortcut: 'Copilot',
      action: () => {
        onClose();
        onOpenAssistant();
      },
    },
    {
      id: 'action-alerts',
      title: 'View Statutory Alerts & Live Stream',
      description: 'High-priority notifications and deficiency broadcasts',
      category: 'Quick Actions',
      icon: Bell,
      shortcut: 'Alerts',
      action: () => {
        onClose();
        onOpenAlerts();
      },
    },
    {
      id: 'action-shortcuts',
      title: 'Keyboard Shortcuts Cheat Sheet',
      description: 'Quick reference for hotkeys (J, K, C, D, T, Esc)',
      category: 'Quick Actions',
      icon: Keyboard,
      shortcut: '?',
      action: () => {
        onClose();
        onOpenShortcuts();
      },
    },
    {
      id: 'action-theme',
      title: `Switch to ${theme === 'dark' ? 'Light' : 'Dark'} Mode`,
      description: 'Toggle visual interface theme preference',
      category: 'Quick Actions',
      icon: theme === 'dark' ? Sun : Moon,
      shortcut: 'T',
      action: () => {
        toggleTheme();
        onClose();
      },
    },

    // Persona Switcher
    {
      id: 'persona-officer',
      title: 'Switch to Scrutiny Officer Persona',
      description: 'Sign in as S. Ramanathan (Senior Scrutiny Officer)',
      category: 'Switch Persona',
      icon: UserCheck,
      action: () => switchPersona('scrutiny@aicte.gov.in'),
    },
    {
      id: 'persona-institution',
      title: 'Switch to Institution Applicant Persona',
      description: 'Sign in as Dr. Suresh Patil (Principal, GEC Pune)',
      category: 'Switch Persona',
      icon: Building2,
      action: () => switchPersona('principal@gecpune.edu.in'),
    },
    {
      id: 'persona-verification',
      title: 'Switch to Verification Bureau Officer Persona',
      description: 'Sign in as Ananya Sharma (Verification Officer)',
      category: 'Switch Persona',
      icon: CheckCircle2,
      action: () => switchPersona('verification@aicte.gov.in'),
    },
    {
      id: 'persona-admin',
      title: 'Switch to System Administrator Persona',
      description: 'Sign in as AICTE System Administrator',
      category: 'Switch Persona',
      icon: ShieldAlert,
      action: () => switchPersona('admin@aicte.gov.in'),
    },
  ];

  const filteredCommands = allCommands.filter((cmd) => {
    const q = query.toLowerCase().trim();
    if (!q) return true;
    return (
      cmd.title.toLowerCase().includes(q) ||
      cmd.description.toLowerCase().includes(q) ||
      cmd.category.toLowerCase().includes(q)
    );
  });

  // Handle keyboard events inside command palette
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev < filteredCommands.length - 1 ? prev + 1 : 0));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev > 0 ? prev - 1 : filteredCommands.length - 1));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (filteredCommands[selectedIndex]) {
        filteredCommands[selectedIndex].action();
      }
    } else if (e.key === 'Escape') {
      e.preventDefault();
      onClose();
    }
  };

  if (!isOpen) return null;

  // Group filtered commands
  const categories = Array.from(new Set(filteredCommands.map((c) => c.category)));

  return (
    <div
      className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-start justify-center pt-16 sm:pt-24 p-4 animate-in fade-in duration-150"
      onClick={onClose}
    >
      <div
        className="w-full max-w-2xl bg-surface border border-border rounded-2xl shadow-modal overflow-hidden flex flex-col max-h-[80vh] animate-in zoom-in-95 duration-150"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Search Input Bar */}
        <div className="p-4 border-b border-border flex items-center gap-3 bg-surface">
          <Search className="w-5 h-5 text-primary flex-shrink-0" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setSelectedIndex(0);
            }}
            onKeyDown={handleKeyDown}
            placeholder="Type a command, navigate to a page, or switch persona..."
            className="flex-1 bg-transparent text-sm font-sans text-text placeholder:text-muted focus:outline-none"
          />
          <kbd className="hidden sm:inline-block px-2 py-0.5 rounded bg-surface-alt border border-border text-[10px] font-mono text-muted font-bold">
            ESC
          </kbd>
        </div>

        {/* Command List grouped by category */}
        <div className="flex-1 overflow-y-auto p-2 divide-y divide-border/40">
          {filteredCommands.length === 0 ? (
            <div className="py-12 text-center text-muted text-xs font-sans">
              No matching command or destination found for &quot;{query}&quot;
            </div>
          ) : (
            categories.map((cat) => {
              const catCommands = filteredCommands.filter((c) => c.category === cat);
              return (
                <div key={cat} className="py-2 first:pt-0 last:pb-0">
                  <div className="px-3 py-1.5 text-[10px] font-mono font-bold uppercase tracking-wider text-muted">
                    {cat}
                  </div>
                  <div className="space-y-0.5">
                    {catCommands.map((cmd) => {
                      const globalIdx = filteredCommands.findIndex((c) => c.id === cmd.id);
                      const isSelected = globalIdx === selectedIndex;
                      const Icon = cmd.icon;

                      return (
                        <div
                          key={cmd.id}
                          onClick={() => cmd.action()}
                          onMouseEnter={() => setSelectedIndex(globalIdx)}
                          className={`px-3 py-2.5 rounded-xl cursor-pointer flex items-center justify-between gap-3 text-xs font-sans transition-all ${
                            isSelected
                              ? 'bg-primary/10 text-primary border border-primary/25 shadow-xs'
                              : 'text-text hover:bg-surface-alt/70'
                          }`}
                        >
                          <div className="flex items-center gap-3 min-w-0">
                            <div
                              className={`p-2 rounded-lg flex-shrink-0 ${
                                isSelected
                                  ? 'bg-primary text-white'
                                  : 'bg-surface-alt text-muted'
                              }`}
                            >
                              <Icon className="w-4 h-4" />
                            </div>
                            <div className="min-w-0">
                              <div className="font-semibold text-text truncate">
                                {cmd.title}
                              </div>
                              <div className="text-[11px] text-muted truncate">
                                {cmd.description}
                              </div>
                            </div>
                          </div>

                          <div className="flex items-center gap-2 flex-shrink-0">
                            {cmd.shortcut && (
                              <kbd className="px-1.5 py-0.5 rounded bg-surface border border-border text-[10px] font-mono font-bold text-muted">
                                {cmd.shortcut}
                              </kbd>
                            )}
                            {isSelected && (
                              <ArrowRight className="w-3.5 h-3.5 text-primary animate-in slide-in-from-left-1" />
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Footer Hints */}
        <div className="p-3 border-t border-border bg-surface-alt/50 flex items-center justify-between text-[11px] font-sans text-muted">
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1">
              <kbd className="px-1.5 py-0.2 rounded bg-surface border border-border font-mono font-bold text-[10px]">↑</kbd>
              <kbd className="px-1.5 py-0.2 rounded bg-surface border border-border font-mono font-bold text-[10px]">↓</kbd>
              <span>to navigate</span>
            </span>
            <span className="flex items-center gap-1">
              <kbd className="px-1.5 py-0.2 rounded bg-surface border border-border font-mono font-bold text-[10px]">↵</kbd>
              <span>to select</span>
            </span>
          </div>
          <span className="hidden sm:inline font-mono text-[10px]">AICTE FIXORA PLATFORM</span>
        </div>
      </div>
    </div>
  );
};
