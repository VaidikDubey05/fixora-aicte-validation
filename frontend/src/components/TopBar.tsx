import React from 'react';
import { Link } from 'react-router-dom';
import {
  Bell,
  Sparkles,
  ShieldCheck,
  User,
  Search,
  Keyboard,
} from 'lucide-react';
import { ThemeToggle } from './ThemeToggle';
import { Role } from '../lib/vocab';
import { useAuth } from '../context/AuthContext';

interface TopBarProps {
  currentRole: Role;
  onRoleChange: (role: Role) => void;
  onOpenAlerts: () => void;
  onOpenAssistant: () => void;
  onOpenCommandPalette?: () => void;
  onOpenShortcuts?: () => void;
  unreadAlertsCount?: number;
  className?: string;
}

export const TopBar: React.FC<TopBarProps> = ({
  currentRole,
  onRoleChange,
  onOpenAlerts,
  onOpenAssistant,
  onOpenCommandPalette,
  onOpenShortcuts,
  unreadAlertsCount = 0,
  className = '',
}) => {
  const { user } = useAuth();

  return (
    <header className={`h-16 px-4 sm:px-6 bg-surface border-b border-border flex items-center justify-between gap-3 sticky top-0 z-30 shadow-xs ${className}`}>
      {/* Brand Emblem & App Title */}
      <Link to="/" className="flex items-center gap-3 group hover:opacity-95 transition-opacity" title="FIXORA Overview & Architecture">
        <div className="w-9 h-9 rounded-xl bg-hero-gradient flex items-center justify-center text-white shadow-glow flex-shrink-0 group-hover:scale-105 transition-transform">
          <ShieldCheck className="w-5 h-5 stroke-[2.5]" />
        </div>
        <div className="flex flex-col">
          <div className="flex items-center gap-2">
            <span className="font-heading font-extrabold text-base tracking-tight text-text">
              FIXORA
            </span>
            <span className="hidden sm:inline-block px-1.5 py-0.2 rounded text-[10px] font-mono font-bold bg-primary/10 text-primary border border-primary/20">
              AICTE EoA 2026-27
            </span>
          </div>
          <span className="text-[11px] text-muted hidden md:inline-block font-sans">
            AI-Assisted Scrutiny & Verification Platform
          </span>
        </div>
      </Link>

      {/* Global Quick Search / Command Palette Trigger */}
      {onOpenCommandPalette && (
        <button
          type="button"
          onClick={onOpenCommandPalette}
          className="hidden md:flex items-center gap-2.5 px-3 py-1.5 rounded-xl border border-border bg-surface-alt/70 text-xs text-muted hover:text-text hover:border-primary/40 hover:bg-surface-alt transition-all shadow-xs"
          title="Search dossiers, actions, and navigate (Ctrl+K)"
        >
          <Search className="w-3.5 h-3.5 text-primary" />
          <span className="font-sans">Quick navigation & dossiers...</span>
          <kbd className="hidden lg:inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded bg-surface border border-border text-[10px] font-mono font-semibold text-muted shadow-xs">
            Ctrl K
          </kbd>
        </button>
      )}

      {/* Role Switcher & Action Controls */}
      <div className="flex items-center gap-2">
        {/* Role Selector Pill */}
        <div className="relative inline-flex items-center bg-surface-alt border border-border rounded-xl p-1 text-xs shadow-xs">
          <span className="text-[11px] font-mono text-muted pl-1.5 pr-1 hidden sm:inline">Role:</span>
          <select
            value={currentRole}
            onChange={(e) => onRoleChange(e.target.value as Role)}
            className="bg-transparent text-xs font-semibold font-sans text-text focus:outline-none cursor-pointer pr-1 py-0.5"
            title="Switch active role context"
          >
            <option value="institution">Institution (Applicant)</option>
            <option value="scrutiny_officer">Scrutiny Officer</option>
            <option value="verification_officer">Verification Bureau</option>
            <option value="admin">System Admin</option>
          </select>
        </div>

        {/* Ask Fixora AI Copilot Trigger */}
        <button
          type="button"
          onClick={onOpenAssistant}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold font-sans bg-primary/10 text-primary border border-primary/25 hover:bg-primary/20 transition-all shadow-xs"
          title="Ask Fixora Handbook & Rule Copilot"
        >
          <Sparkles className="w-3.5 h-3.5 text-primary" />
          <span className="hidden lg:inline">Ask Fixora</span>
        </button>

        {/* Statutory Alerts Drawer Toggle */}
        <button
          type="button"
          onClick={onOpenAlerts}
          className="relative p-2 rounded-xl border border-border bg-surface text-muted hover:text-text hover:bg-surface-alt transition-colors shadow-xs"
          title="Statutory Alerts & Deficiencies"
          aria-label="Statutory Alerts"
        >
          <Bell className="w-4 h-4" />
          {unreadAlertsCount > 0 && (
            <span className="absolute top-1 right-1 w-4 h-4 rounded-full bg-danger text-white text-[9px] font-mono font-bold flex items-center justify-center shadow-xs">
              {unreadAlertsCount}
            </span>
          )}
        </button>

        {/* Keyboard Shortcuts Trigger */}
        {onOpenShortcuts && (
          <button
            type="button"
            onClick={onOpenShortcuts}
            className="hidden sm:flex p-2 rounded-xl border border-border bg-surface text-muted hover:text-text hover:bg-surface-alt transition-colors shadow-xs"
            title="Keyboard Shortcuts Cheat Sheet (?)"
            aria-label="Keyboard Shortcuts"
          >
            <Keyboard className="w-4 h-4" />
          </button>
        )}

        {/* Animated Sun/Moon Theme Toggle */}
        <ThemeToggle />

        {/* User Identity Avatar */}
        <div className="flex items-center gap-2 pl-1 border-l border-border">
          <div
            className="w-8 h-8 rounded-full bg-hero-gradient flex items-center justify-center text-white font-mono text-xs font-bold shadow-xs cursor-default"
            title={`${user?.full_name || 'User'} (${user?.role || currentRole})`}
          >
            {user?.full_name ? user.full_name.charAt(0).toUpperCase() : <User className="w-4 h-4" />}
          </div>
        </div>
      </div>
    </header>
  );
};
