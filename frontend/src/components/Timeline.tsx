import React from 'react';
import { LucideIcon, ShieldCheck, Clock, User } from 'lucide-react';

export interface TimelineEvent {
  id: string;
  title: string;
  timestamp: string;
  actor: string;
  role?: string;
  description?: string;
  icon?: LucideIcon;
  status?: 'completed' | 'in_progress' | 'flagged' | 'pending';
  hash?: string; // SHA-256 cryptographic chain block hash
  verifiedChain?: boolean;
}

interface TimelineProps {
  events: TimelineEvent[];
  className?: string;
}

export const Timeline: React.FC<TimelineProps> = ({ events, className = '' }) => {
  return (
    <div className={`relative pl-6 space-y-6 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-border ${className}`}>
      {events.map((event) => {
        const Icon = event.icon || Clock;

        return (
          <div key={event.id} className="relative group">
            <div
              className={`absolute -left-6 top-1 w-5 h-5 rounded-full border-2 flex items-center justify-center transition-all bg-surface ${
                event.status === 'completed'
                  ? 'border-success text-success'
                  : event.status === 'flagged'
                  ? 'border-warning text-warning'
                  : 'border-primary text-primary'
              }`}
            >
              <span
                className={`w-2 h-2 rounded-full ${
                  event.status === 'completed'
                    ? 'bg-success'
                    : event.status === 'flagged'
                    ? 'bg-warning'
                    : 'bg-primary'
                }`}
              />
            </div>

            <div className="bg-surface rounded-xl border border-border p-4 shadow-card hover:border-primary/30 transition-all">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 pb-1 border-b border-border/50">
                <div className="flex items-center gap-2">
                  <Icon className="w-4 h-4 text-primary" />
                  <h4 className="text-sm font-semibold font-heading text-text">
                    {event.title}
                  </h4>
                </div>
                <span className="text-[11px] font-mono text-muted">
                  {event.timestamp}
                </span>
              </div>

              <div className="mt-2 flex items-center gap-2 text-xs text-muted">
                <User className="w-3.5 h-3.5 text-muted/80" />
                <span className="font-medium text-text">{event.actor}</span>
                {event.role && (
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-surface-alt border border-border font-mono">
                    {event.role}
                  </span>
                )}
              </div>

              {event.description && (
                <p className="mt-2 text-xs text-text/80 leading-relaxed font-sans">
                  {event.description}
                </p>
              )}

              {event.hash && (
                <div className="mt-3 pt-2 border-t border-border/50 flex flex-wrap items-center justify-between gap-2 text-[10px] font-mono text-muted">
                  <div className="flex items-center gap-1.5 truncate max-w-full">
                    <span className="text-muted/60">SHA-256:</span>
                    <span className="bg-surface-alt px-1.5 py-0.5 rounded text-primary truncate max-w-[220px]">
                      {event.hash}
                    </span>
                  </div>
                  {event.verifiedChain !== false && (
                    <span className="inline-flex items-center gap-1 text-success font-medium">
                      <ShieldCheck className="w-3 h-3" /> Block Verified
                    </span>
                  )}
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
};
