import React from 'react';
import { LucideIcon, FolderSearch } from 'lucide-react';

interface EmptyStateProps {
  title: string;
  description: string;
  icon?: LucideIcon;
  actionText?: string;
  onAction?: () => void;
  secondaryActionText?: string;
  onSecondaryAction?: () => void;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title,
  description,
  icon: Icon = FolderSearch,
  actionText,
  onAction,
  secondaryActionText,
  onSecondaryAction,
  className = '',
}) => {
  return (
    <div
      className={`rounded-card border border-dashed border-border bg-surface/50 p-10 flex flex-col items-center justify-center text-center max-w-lg mx-auto ${className}`}
    >
      <div className="w-14 h-14 rounded-2xl bg-surface-alt border border-border flex items-center justify-center text-primary mb-4 shadow-xs">
        <Icon className="w-7 h-7" />
      </div>

      <h3 className="text-base font-bold font-heading text-text">
        {title}
      </h3>

      <p className="mt-2 text-xs text-muted max-w-sm leading-relaxed font-sans">
        {description}
      </p>

      {(actionText || secondaryActionText) && (
        <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
          {actionText && onAction && (
            <button
              type="button"
              onClick={onAction}
              className="px-4 py-2 rounded-xl text-xs font-semibold font-sans bg-hero-gradient text-white shadow-glow hover:brightness-105 active:scale-95 transition-all"
            >
              {actionText}
            </button>
          )}

          {secondaryActionText && onSecondaryAction && (
            <button
              type="button"
              onClick={onSecondaryAction}
              className="px-4 py-2 rounded-xl text-xs font-semibold font-sans bg-surface-alt text-primary border border-border hover:bg-border/60 transition-colors"
            >
              {secondaryActionText}
            </button>
          )}
        </div>
      )}
    </div>
  );
};
