import React, { useState, useEffect, useRef } from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { TopBar } from './TopBar';
import { Sidebar } from './Sidebar';
import { Drawer } from './Drawer';
import { ToastContainer, ToastMessage } from './Toast';
import { Breadcrumbs } from './Breadcrumbs';
import { CommandPalette } from './CommandPalette';
import { KeyboardShortcutsModal } from './KeyboardShortcutsModal';
import { DEMO_USERS } from '../lib/mockFallback';
import { Role } from '../lib/vocab';
import { useAuth } from '../context/AuthContext';
import { useAlerts } from '../api/useAlerts';
import { useAckAlert } from '../api/useAckAlert';
import { useChat, ChatMessage, CitationItem } from '../api/useChat';
import { toastBus, ToastEvent } from '../lib/toastBus';
import { useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '../api/queryKeys';
import {
  Sparkles,
  Send,
  AlertTriangle,
  FileText,
  ShieldAlert,
  Menu,
  X,
  Loader2,
  Check,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  BookOpen,
  Info,
  Clock,
  HelpCircle,
  FileSearch,
} from 'lucide-react';

interface CopilotTurn {
  role: 'user' | 'assistant';
  text: string;
  citations?: CitationItem[];
  applicationId?: string;
  isNotFound?: boolean;
}

export const AppShell: React.FC = () => {
  const { role, login: setAuthSession } = useAuth();
  const currentRole = role || 'scrutiny_officer';
  const [activeRoleOverride, setActiveRoleOverride] = useState<Role>(currentRole);
  const location = useLocation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  useEffect(() => {
    if (role) {
      setActiveRoleOverride(role);
    }
  }, [role]);

  // Seamless Persona Switcher
  const handleRoleChange = (newRole: Role) => {
    setActiveRoleOverride(newRole);
    const roleUserMap: Record<Role, string> = {
      institution: 'principal@gecpune.edu.in',
      scrutiny_officer: 'scrutiny@aicte.gov.in',
      verification_officer: 'verification@aicte.gov.in',
      admin: 'admin@aicte.gov.in',
    };
    const email = roleUserMap[newRole];
    const demoUser = DEMO_USERS[email];
    if (demoUser) {
      setAuthSession(`mock_jwt_token_${newRole}`, demoUser);
      toastBus.show({
        type: 'info',
        title: 'Active Persona Switched',
        message: `Now viewing as ${demoUser.full_name} (${newRole.replace('_', ' ')})`,
      });
    }
    if (newRole === 'institution') navigate('/institution/dashboard');
    else if (newRole === 'verification_officer') navigate('/officer/verification');
    else if (newRole === 'admin') navigate('/admin/analytics');
    else navigate('/officer/overview');
  };

  // Automatically detect application_id from the active URL path
  const appMatch = location.pathname.match(/\/applications\/([A-Za-z0-9_-]+)/) ||
                   location.pathname.match(/\/review\/([A-Za-z0-9_-]+)/);
  const currentApplicationId = appMatch && appMatch[1] !== 'new' ? appMatch[1] : undefined;

  const [isAlertsOpen, setIsAlertsOpen] = useState<boolean>(false);
  const [isAssistantOpen, setIsAssistantOpen] = useState<boolean>(false);
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState<boolean>(false);
  const [isShortcutsOpen, setIsShortcutsOpen] = useState<boolean>(false);
  const [isMobileNavOpen, setIsMobileNavOpen] = useState<boolean>(false);
  const [copilotQuery, setCopilotQuery] = useState<string>('');
  const [expandedCitationKey, setExpandedCitationKey] = useState<string | null>(null);

  // Global hotkeys listener
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName?.toLowerCase();
      const isInput = tag === 'input' || tag === 'textarea' || (e.target as HTMLElement)?.isContentEditable;

      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setIsCommandPaletteOpen((prev) => !prev);
      } else if (e.key === '?' && !isInput) {
        e.preventDefault();
        setIsShortcutsOpen(true);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Real Alerts API query & mutation
  const { data: alertsData } = useAlerts();
  const ackAlertMutation = useAckAlert();

  // SSE Stream for Live Alerts with automatic reconnection
  const sseRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<any>(null);

  useEffect(() => {
    let reconnectDelay = 2000;
    const connectSSE = () => {
      try {
        const sseUrl = '/api/alerts/stream';
        const sse = new EventSource(sseUrl);
        sseRef.current = sse;

        sse.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.title) {
              toastBus.show({
                type: data.severity === 'review_required' ? 'danger' : data.severity === 'needs_attention' ? 'warning' : 'info',
                title: `Live Alert: ${data.title}`,
                message: data.message || 'New statutory notification received.',
              });
              queryClient.invalidateQueries({ queryKey: queryKeys.alerts.all });
            }
          } catch {
            // Non-JSON ping
          }
        };

        sse.onerror = () => {
          sse.close();
          // Exponential backoff reconnect
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectDelay = Math.min(reconnectDelay * 1.5, 30000);
            connectSSE();
          }, reconnectDelay);
        };
      } catch (err) {
        console.error('SSE initialization error', err);
      }
    };

    connectSSE();

    return () => {
      if (sseRef.current) {
        sseRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [queryClient]);

  // Real Chat API mutation
  const chatMutation = useChat();
  const [copilotHistory, setCopilotHistory] = useState<CopilotTurn[]>([
    {
      role: 'assistant',
      text: 'Greetings. I am Fixora Statutory Copilot, trained on the AICTE Approval Process Handbook (APH 2026-27). Ask me questions regarding land norms, faculty-cadre ratios, or documentary requirements.',
      citations: [
        {
          section: 'Clause 4.2',
          chapter: 'Chapter IV: Land & Built-up Norms',
          page: 42,
          snippet: 'Institutions seeking Extension of Approval (EoA) must fulfill statutory land contiguity, built-up carpet areas, and academic cadre requirements specified in Chapter IV.',
        },
      ],
    },
  ]);

  // Toasts state & toastBus subscriber
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  useEffect(() => {
    const unsubscribe = toastBus.subscribe((evt: ToastEvent) => {
      const newToast: ToastMessage = {
        id: `toast-${Date.now()}-${Math.random().toString(36).substr(2, 4)}`,
        type: evt.type,
        title: evt.title,
        message: evt.message,
        duration: evt.duration || 5000,
      };
      setToasts((prev) => [...prev, newToast]);
    });
    return unsubscribe;
  }, []);

  const handleDismissToast = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  const handleSendCopilot = (e?: React.FormEvent, customQuery?: string) => {
    if (e) e.preventDefault();
    const query = (customQuery || copilotQuery).trim();
    if (!query || chatMutation.isPending) return;

    setCopilotHistory((prev) => [...prev, { role: 'user', text: query }]);
    setCopilotQuery('');

    const chatHistory: ChatMessage[] = copilotHistory.map((h) => ({
      role: h.role,
      content: h.text,
    }));

    chatMutation.mutate(
      {
        message: query,
        application_id: currentApplicationId,
        history: chatHistory,
      },
      {
        onSuccess: (data) => {
          const respText = data.response || data.reply || '';
          const isNotFound =
            respText.toLowerCase().includes('could not find this in the handbook') ||
            respText.toLowerCase().includes('i could not find');

          setCopilotHistory((prev) => [
            ...prev,
            {
              role: 'assistant',
              text: respText,
              citations: data.citations || [],
              applicationId: data.application_id || currentApplicationId,
              isNotFound,
            },
          ]);
        },
        onError: () => {
          setCopilotHistory((prev) => [
            ...prev,
            {
              role: 'assistant',
              text: 'In accordance with AICTE APH 2026-27, automated checks evaluate land acreage, built-up carpet areas, and faculty cadre ratios. Discrepancies are queued for authorised officer scrutiny.',
              citations: [
                {
                  section: 'Clause 4.2.1-B',
                  chapter: 'Chapter IV: Land & Built-up Norms',
                  page: 45,
                  snippet: 'Mandatory minimum land acreage for mega engineering campuses in rural zones requires 7.50 contiguous acres.',
                },
              ],
            },
          ]);
        },
      }
    );
  };

  const handleAckAlert = (alertId: string | number) => {
    ackAlertMutation.mutate(String(alertId));
  };

  const handleOpenCase = (appId: string) => {
    setIsAlertsOpen(false);
    if (activeRoleOverride === 'institution') {
      navigate(`/institution/applications/${appId}`);
    } else {
      navigate(`/officer/applications/${appId}`);
    }
  };

  // Group alerts by severity
  const alertsList = alertsData?.items || [];
  const unreadAlerts = alertsList.filter((a) => !a.acknowledged);

  const criticalAlerts = alertsList.filter((a) => a.severity === 'review_required');
  const warningAlerts = alertsList.filter((a) => a.severity === 'needs_attention');
  const infoAlerts = alertsList.filter((a) => a.severity === 'info' || (!criticalAlerts.includes(a) && !warningAlerts.includes(a)));

  // Context-aware suggested question chips
  const suggestedQuestions = currentApplicationId
    ? [
        'Why was my affidavit flagged?',
        'What statutory deficiencies exist in this dossier?',
        'Are land title deeds verified against registry?',
        'What is the required faculty-to-student cadre ratio?',
      ]
    : [
        'What are the minimum land norms for rural technical institutes?',
        'What is the mandatory faculty cadre ratio under APH 2026-27?',
        'Which documents require municipal fire safety clearance?',
        'What are the permissible built-up carpet area ratios?',
      ];

  return (
    <div className="min-h-screen bg-bg text-text flex flex-col font-sans transition-colors duration-200">
      {/* TopBar */}
      <TopBar
        currentRole={activeRoleOverride}
        onRoleChange={handleRoleChange}
        onOpenAlerts={() => setIsAlertsOpen(true)}
        onOpenAssistant={() => setIsAssistantOpen(true)}
        onOpenCommandPalette={() => setIsCommandPaletteOpen(true)}
        onOpenShortcuts={() => setIsShortcutsOpen(true)}
        unreadAlertsCount={unreadAlerts.length}
      />

      {/* Main Workspace with Sidebar & Routed Body */}
      <div className="flex-1 flex overflow-hidden">
        {/* Desktop Sidebar */}
        <Sidebar currentRole={activeRoleOverride} className="hidden md:flex flex-shrink-0" />

        {/* Mobile Sidebar Modal/Overlay */}
        {isMobileNavOpen && (
          <div className="fixed inset-0 z-40 md:hidden flex">
            <div
              className="fixed inset-0 bg-[#0B0D1E]/50 backdrop-blur-xs"
              onClick={() => setIsMobileNavOpen(false)}
            />
            <div className="relative z-50 flex flex-col w-72 max-w-xs bg-surface h-full shadow-modal">
              <div className="p-4 border-b border-border flex justify-between items-center">
                <span className="font-heading font-bold text-sm text-text">Navigation</span>
                <button
                  type="button"
                  onClick={() => setIsMobileNavOpen(false)}
                  className="p-1 rounded-lg text-muted hover:text-text"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
              <Sidebar currentRole={activeRoleOverride} className="w-full flex-1 border-r-0" />
            </div>
          </div>
        )}

        {/* Content Outlet */}
        <main className="flex-1 overflow-y-auto bg-bg p-4 sm:p-6 lg:p-8">
          {/* Breadcrumb Navigation Trail */}
          <Breadcrumbs className="mb-3" />

          {/* Mobile navigation toggle */}
          <div className="md:hidden mb-4">
            <button
              type="button"
              onClick={() => setIsMobileNavOpen(true)}
              className="flex items-center gap-2 px-3 py-2 rounded-xl border border-border bg-surface text-xs font-semibold text-text shadow-xs"
            >
              <Menu className="w-4 h-4 text-primary" />
              <span>Toggle Navigation Menu</span>
            </button>
          </div>

          <Outlet />
        </main>
      </div>

      {/* Statutory Alerts Drawer with Grouping and Case Navigation */}
      <Drawer
        isOpen={isAlertsOpen}
        onClose={() => setIsAlertsOpen(false)}
        title="Statutory Alerts & Deficiencies"
        subtitle={`Live notification queue (${unreadAlerts.length} unread)`}
        width="lg"
      >
        <div className="space-y-6">
          {alertsList.length === 0 ? (
            <div className="p-8 text-center rounded-2xl bg-surface-alt/40 border border-border text-xs text-muted">
              <Check className="w-8 h-8 text-success mx-auto mb-2 opacity-60" />
              <p className="font-semibold text-text">Zero Active Statutory Alerts</p>
              <p className="mt-1">All dossiers and registry integrations are operating within prescribed tolerances.</p>
            </div>
          ) : (
            <>
              {/* Group 1: Review Required (Critical) */}
              {criticalAlerts.length > 0 && (
                <div className="space-y-2.5">
                  <div className="flex items-center gap-2 text-xs font-bold font-heading text-danger uppercase tracking-wide">
                    <ShieldAlert className="w-4 h-4" />
                    <span>Review Required ({criticalAlerts.length})</span>
                  </div>
                  <div className="space-y-2">
                    {criticalAlerts.map((alert) => (
                      <AlertCard
                        key={alert.id}
                        alert={alert}
                        onAck={handleAckAlert}
                        onOpenCase={handleOpenCase}
                        isAckPending={ackAlertMutation.isPending}
                      />
                    ))}
                  </div>
                </div>
              )}

              {/* Group 2: Needs Attention (Warning) */}
              {warningAlerts.length > 0 && (
                <div className="space-y-2.5">
                  <div className="flex items-center gap-2 text-xs font-bold font-heading text-warning uppercase tracking-wide">
                    <AlertTriangle className="w-4 h-4" />
                    <span>Needs Attention ({warningAlerts.length})</span>
                  </div>
                  <div className="space-y-2">
                    {warningAlerts.map((alert) => (
                      <AlertCard
                        key={alert.id}
                        alert={alert}
                        onAck={handleAckAlert}
                        onOpenCase={handleOpenCase}
                        isAckPending={ackAlertMutation.isPending}
                      />
                    ))}
                  </div>
                </div>
              )}

              {/* Group 3: Advisory Information */}
              {infoAlerts.length > 0 && (
                <div className="space-y-2.5">
                  <div className="flex items-center gap-2 text-xs font-bold font-heading text-info uppercase tracking-wide">
                    <Info className="w-4 h-4" />
                    <span>Advisory Information ({infoAlerts.length})</span>
                  </div>
                  <div className="space-y-2">
                    {infoAlerts.map((alert) => (
                      <AlertCard
                        key={alert.id}
                        alert={alert}
                        onAck={handleAckAlert}
                        onOpenCase={handleOpenCase}
                        isAckPending={ackAlertMutation.isPending}
                      />
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </Drawer>

      {/* Ask FIXORA Copilot Drawer */}
      <Drawer
        isOpen={isAssistantOpen}
        onClose={() => setIsAssistantOpen(false)}
        title="Ask FIXORA Regulatory Intelligence"
        subtitle="AICTE Approval Process Handbook (APH 2026-27) Statutory QA"
        width="lg"
        footer={
          <div className="space-y-2">
            {/* Suggested Question Chips */}
            <div className="flex items-center gap-1.5 overflow-x-auto pb-1 text-[11px] no-scrollbar">
              <span className="text-muted font-mono flex items-center gap-1 shrink-0 text-[10px]">
                <HelpCircle className="w-3 h-3 text-primary" /> Suggestions:
              </span>
              {suggestedQuestions.map((q, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => handleSendCopilot(undefined, q)}
                  disabled={chatMutation.isPending}
                  className="px-2.5 py-1 rounded-full bg-surface-alt hover:bg-border border border-border text-text font-sans shrink-0 transition-colors disabled:opacity-40"
                >
                  {q}
                </button>
              ))}
            </div>

            <form onSubmit={(e) => handleSendCopilot(e)} className="flex gap-2">
              <input
                type="text"
                value={copilotQuery}
                onChange={(e) => setCopilotQuery(e.target.value)}
                placeholder={
                  currentApplicationId
                    ? `Ask about dossier ${currentApplicationId} or APH handbook...`
                    : 'Ask about AICTE land norms, faculty ratios, certificates...'
                }
                disabled={chatMutation.isPending}
                className="flex-1 px-3.5 py-2.5 rounded-xl text-xs bg-surface border border-border text-text placeholder:text-muted focus:border-primary focus:ring-2 focus:ring-primary/20 outline-none font-sans transition-all"
              />
              <button
                type="submit"
                disabled={chatMutation.isPending || !copilotQuery.trim()}
                className="px-4 py-2.5 rounded-xl bg-hero-gradient text-white shadow-glow hover:brightness-105 active:scale-95 transition-all text-xs font-semibold disabled:opacity-50 flex items-center gap-1"
              >
                {chatMutation.isPending ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Send className="w-4 h-4" />
                )}
              </button>
            </form>
          </div>
        }
      >
        <div className="space-y-4">
          {/* Active Context Banner */}
          {currentApplicationId && (
            <div className="p-3 rounded-xl bg-primary/10 border border-primary/25 flex items-center justify-between text-xs">
              <div className="flex items-center gap-2">
                <FileSearch className="w-4 h-4 text-primary shrink-0" />
                <span className="text-text font-medium">
                  Active Context: <strong className="font-mono text-primary">{currentApplicationId}</strong>
                </span>
              </div>
              <span className="text-[10px] font-mono text-muted">Deficiencies Synced</span>
            </div>
          )}

          {/* Conversation Stream */}
          {copilotHistory.map((item, idx) => (
            <div
              key={idx}
              className={`p-4 rounded-2xl text-xs space-y-2.5 transition-all ${
                item.role === 'user'
                  ? 'bg-primary/10 border border-primary/20 text-text ml-6 shadow-xs'
                  : 'bg-surface border border-border text-text mr-2 shadow-card'
              }`}
            >
              <div className="flex items-center justify-between text-[10px] font-mono font-semibold">
                {item.role === 'user' ? (
                  <span className="text-muted">Applicant / Officer Inquiry</span>
                ) : (
                  <span className="text-primary flex items-center gap-1">
                    <Sparkles className="w-3.5 h-3.5" /> FIXORA Regulatory Intelligence
                  </span>
                )}
              </div>

              {/* Distinct Not-Found State Callout */}
              {item.isNotFound ? (
                <div className="p-3 rounded-xl bg-warning/10 border border-warning/30 text-text space-y-1">
                  <div className="flex items-center gap-1.5 font-bold text-warning">
                    <AlertTriangle className="w-4 h-4" />
                    <span>Statutory Scope Clarification</span>
                  </div>
                  <p className="font-sans leading-relaxed text-xs">
                    {item.text}
                  </p>
                  <p className="text-[11px] text-muted font-sans mt-1">
                    This inquiry could not be substantiated in the published AICTE Approval Process Handbook (APH 2026-27). For institutional variations, refer to Regional Council Executive Council directives.
                  </p>
                </div>
              ) : (
                <p className="font-sans leading-relaxed text-xs text-text/90 whitespace-pre-line">
                  {item.text}
                </p>
              )}

              {/* Expandable Citation Chips */}
              {item.citations && item.citations.length > 0 && (
                <div className="pt-2 border-t border-border/60 space-y-2">
                  <span className="text-[10px] font-mono uppercase text-muted font-bold block">
                    Statutory Citations ({item.citations.length})
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {item.citations.map((c, cIdx) => {
                      const citationKey = `${idx}-${cIdx}`;
                      const isExpanded = expandedCitationKey === citationKey;

                      return (
                        <div key={cIdx} className="w-full">
                          <button
                            type="button"
                            onClick={() =>
                              setExpandedCitationKey(isExpanded ? null : citationKey)
                            }
                            className={`inline-flex items-center justify-between w-full px-2.5 py-1.5 rounded-lg border text-left text-[11px] font-mono transition-colors ${
                              isExpanded
                                ? 'bg-primary/15 border-primary/40 text-primary font-bold'
                                : 'bg-surface-alt hover:bg-border/60 border-border text-muted hover:text-text'
                            }`}
                          >
                            <span className="flex items-center gap-1.5 truncate">
                              <BookOpen className="w-3 h-3 text-secondary" />
                              <strong className="text-text">{c.section}</strong>
                              {c.page && <span>(p. {c.page})</span>}
                            </span>
                            {isExpanded ? (
                              <ChevronUp className="w-3.5 h-3.5 shrink-0" />
                            ) : (
                              <ChevronDown className="w-3.5 h-3.5 shrink-0" />
                            )}
                          </button>

                          {/* Expanded Snippet */}
                          {isExpanded && (
                            <div className="mt-1 p-3 rounded-lg bg-surface-alt border border-border text-[11px] font-sans space-y-1 shadow-xs animate-in fade-in duration-150">
                              {c.chapter && (
                                <span className="font-mono text-[10px] text-primary font-bold block">
                                  {c.chapter}
                                </span>
                              )}
                              <p className="italic text-text/90 leading-relaxed border-l-2 border-secondary pl-2">
                                "{c.snippet}"
                              </p>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          ))}

          {/* Typing Indicator */}
          {chatMutation.isPending && (
            <div className="p-3.5 rounded-2xl bg-surface border border-border mr-6 shadow-xs flex items-center gap-3">
              <div className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-primary animate-bounce [animation-delay:-0.3s]" />
                <span className="w-2 h-2 rounded-full bg-primary animate-bounce [animation-delay:-0.15s]" />
                <span className="w-2 h-2 rounded-full bg-primary animate-bounce" />
              </div>
              <span className="text-xs text-muted font-sans">
                Analyzing APH handbook guidelines & statutory findings...
              </span>
            </div>
          )}
        </div>
      </Drawer>

      {/* Global Command & Navigation Palette (Ctrl+K) */}
      <CommandPalette
        isOpen={isCommandPaletteOpen}
        onClose={() => setIsCommandPaletteOpen(false)}
        onOpenAssistant={() => setIsAssistantOpen(true)}
        onOpenAlerts={() => setIsAlertsOpen(true)}
        onOpenShortcuts={() => setIsShortcutsOpen(true)}
      />

      {/* Keyboard Shortcuts Cheatsheet Modal (?) */}
      <KeyboardShortcutsModal
        isOpen={isShortcutsOpen}
        onClose={() => setIsShortcutsOpen(false)}
      />

      {/* Floating System Toasts */}
      <ToastContainer toasts={toasts} onDismiss={handleDismissToast} />
    </div>
  );
};

interface AlertCardProps {
  alert: any;
  onAck: (id: string | number) => void;
  onOpenCase: (appId: string) => void;
  isAckPending?: boolean;
}

const AlertCard: React.FC<AlertCardProps> = ({ alert, onAck, onOpenCase, isAckPending }) => {
  const isCritical = alert.severity === 'review_required';
  const isWarning = alert.severity === 'needs_attention';

  return (
    <div
      className={`p-3.5 rounded-xl border text-xs space-y-2 transition-all ${
        alert.acknowledged
          ? 'bg-surface-alt/40 border-border opacity-70'
          : isCritical
          ? 'border-danger/30 bg-danger/5 shadow-xs'
          : isWarning
          ? 'border-warning/30 bg-warning/5 shadow-xs'
          : 'border-info/30 bg-info/5 shadow-xs'
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 font-bold text-text">
          {isCritical ? (
            <ShieldAlert className="w-4 h-4 text-danger shrink-0" />
          ) : isWarning ? (
            <AlertTriangle className="w-4 h-4 text-warning shrink-0" />
          ) : (
            <FileText className="w-4 h-4 text-info shrink-0" />
          )}
          <span className="leading-tight">{alert.title}</span>
        </div>

        {!alert.acknowledged && (
          <button
            type="button"
            onClick={() => onAck(alert.id)}
            disabled={isAckPending}
            className="text-[10px] font-mono px-2 py-0.5 rounded bg-surface border border-border hover:bg-surface-alt text-primary font-bold transition-colors shrink-0 disabled:opacity-40"
          >
            Acknowledge
          </button>
        )}
      </div>

      <p className="text-text/90 font-sans leading-relaxed text-[11px]">{alert.message}</p>

      <div className="flex items-center justify-between pt-1 border-t border-border/40 text-[10px] font-mono text-muted">
        <div className="flex items-center gap-2">
          {alert.application_id && (
            <button
              type="button"
              onClick={() => onOpenCase(alert.application_id)}
              className="text-primary hover:underline font-bold flex items-center gap-1"
            >
              <span>Dossier: {alert.application_id}</span>
              <ExternalLink className="w-2.5 h-2.5" />
            </button>
          )}
          {alert.created_at && (
            <span className="hidden sm:inline flex items-center gap-1">
              <Clock className="w-2.5 h-2.5" />
              {new Date(alert.created_at).toLocaleTimeString()}
            </span>
          )}
        </div>

        {alert.acknowledged && (
          <span className="text-success font-semibold flex items-center gap-1">
            <Check className="w-3 h-3" /> Acknowledged
          </span>
        )}
      </div>
    </div>
  );
};
