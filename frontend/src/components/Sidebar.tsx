import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  FilePlus,
  ClipboardList,
  Building2,
  ShieldCheck,
  Code,
  BarChart3,
  Database,
  Lock,
  LogOut,
  LucideIcon,
  Users,
  Sparkles,
} from 'lucide-react';
import { Role } from '../lib/vocab';
import { useAuth } from '../context/AuthContext';

interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  badge?: string | number;
}

interface SidebarProps {
  currentRole: Role;
  className?: string;
}

export const Sidebar: React.FC<SidebarProps> = ({ currentRole, className = '' }) => {
  const { user, logout } = useAuth();

  const getNavItems = (role: Role): { group: string; items: NavItem[] }[] => {
    switch (role) {
      case 'institution':
        return [
          {
            group: 'Institution Portal',
            items: [
              {
                to: '/institution/dashboard',
                label: 'Scrutiny Dashboard',
                icon: LayoutDashboard,
              },
              {
                to: '/institution/submit',
                label: 'New EoA Submission',
                icon: FilePlus,
              },
            ],
          },
        ];

      case 'scrutiny_officer':
        return [
          {
            group: 'Scrutiny Bureau',
            items: [
              {
                to: '/officer/overview',
                label: 'Bureau Overview',
                icon: LayoutDashboard,
              },
              {
                to: '/officer/queue',
                label: 'Applications Queue',
                icon: ClipboardList,
              },
              {
                to: '/officer/inspection',
                label: 'Inspection Queue',
                icon: Building2,
              },
            ],
          },
        ];

      case 'verification_officer':
        return [
          {
            group: 'Verification Bureau',
            items: [
              {
                to: '/officer/verification',
                label: 'Verification Queue',
                icon: ShieldCheck,
              },
              {
                to: '/officer/inspection',
                label: 'Spatial & Land Queue',
                icon: Building2,
              },
            ],
          },
        ];

      case 'admin':
        return [
          {
            group: 'Statutory Administration',
            items: [
              {
                to: '/admin/analytics',
                label: 'Operational Analytics',
                icon: BarChart3,
              },
              {
                to: '/admin/rules',
                label: 'Rule Packs Registry',
                icon: Database,
              },
              {
                to: '/admin/rules/editor',
                label: 'Rule Specification IDE',
                icon: Code,
              },
              {
                to: '/admin/audit',
                label: 'Audit Chain Explorer',
                icon: Lock,
              },
              {
                to: '/admin/users',
                label: 'Access & User Directory',
                icon: Users,
              },
            ],
          },
        ];
    }
  };

  const navGroups = getNavItems(currentRole);

  return (
    <aside className={`w-64 bg-surface border-r border-border flex flex-col justify-between p-4 shadow-xs select-none ${className}`}>
      {/* Navigation Links */}
      <div className="space-y-6">
        {navGroups.map((group, gIndex) => (
          <div key={gIndex} className="space-y-1">
            <p className="px-3 text-[10px] uppercase font-mono font-bold tracking-wider text-muted">
              {group.group}
            </p>
            <div className="mt-2 space-y-1">
              {group.items.map((item) => {
                const Icon = item.icon;
                return (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    className={({ isActive }) =>
                      `flex items-center justify-between px-3 py-2.5 rounded-xl text-xs font-semibold font-sans transition-all duration-200 group ${
                        isActive
                          ? 'bg-primary/10 text-primary border border-primary/25 shadow-xs font-bold'
                          : 'text-text/80 hover:text-text hover:bg-surface-alt border border-transparent'
                      }`
                    }
                  >
                    <div className="flex items-center gap-2.5">
                      <Icon className="w-4 h-4 text-muted group-hover:text-primary transition-colors" />
                      <span>{item.label}</span>
                    </div>

                    {item.badge !== undefined && (
                      <span className="px-1.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-surface-alt border border-border text-primary">
                        {item.badge}
                      </span>
                    )}
                  </NavLink>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      {/* Bottom User Portal Status & Logout */}
      <div className="pt-4 border-t border-border space-y-3">
        <div className="p-3 rounded-xl bg-surface-alt/60 border border-border text-xs">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-mono text-muted uppercase">Signed in as</span>
            <span className="w-2 h-2 rounded-full bg-success inline-block" />
          </div>
          <p className="mt-1 font-bold text-text truncate">
            {user?.full_name || 'Authenticated Officer'}
          </p>
          <p className="text-[10px] text-muted font-mono truncate">
            {user?.email || 'officer@aicte.gov.in'}
          </p>
        </div>

        <NavLink
          to="/"
          className="w-full flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-semibold text-primary hover:bg-primary/10 transition-colors text-left"
        >
          <Sparkles className="w-4 h-4 text-secondary" />
          <span>Platform Overview</span>
        </NavLink>

        <button
          type="button"
          onClick={logout}
          className="w-full flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-semibold text-danger/80 hover:text-danger hover:bg-danger/10 transition-colors text-left"
        >
          <LogOut className="w-4 h-4" />
          <span>Exit Session (Logout)</span>
        </button>
      </div>
    </aside>
  );
};
