import React from 'react';
import { LucideIcon, TrendingUp, TrendingDown, Minus } from 'lucide-react';

interface KpiCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: LucideIcon;
  trend?: {
    value: string | number;
    direction: 'up' | 'down' | 'neutral';
    label?: string;
  };
  badge?: {
    text: string;
    variant?: 'primary' | 'secondary' | 'accent' | 'success' | 'warning' | 'danger';
  };
  onClick?: () => void;
  className?: string;
}

export const KpiCard: React.FC<KpiCardProps> = ({
  title,
  value,
  subtitle,
  icon: Icon,
  trend,
  badge,
  onClick,
  className = '',
}) => {
  const badgeColors = {
    primary: 'bg-primary/10 text-primary border-primary/20',
    secondary: 'bg-secondary/15 text-secondary border-secondary/30',
    accent: 'bg-accent/15 text-accent border-accent/30',
    success: 'bg-success/12 text-success border-success/30',
    warning: 'bg-warning/15 text-warning border-warning/30',
    danger: 'bg-danger/12 text-danger border-danger/30',
  };

  return (
    <div
      onClick={onClick}
      className={`rounded-card bg-surface border border-border p-5 shadow-card transition-all duration-200 ${
        onClick ? 'cursor-pointer hover:border-primary/40 hover:shadow-floating' : ''
      } ${className}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-medium text-muted tracking-wide uppercase font-mono">
            {title}
          </p>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold font-heading text-text tracking-tight">
              {value}
            </span>
            {badge && (
              <span
                className={`text-[11px] font-mono font-semibold px-2 py-0.5 rounded-full border ${
                  badgeColors[badge.variant || 'primary']
                }`}
              >
                {badge.text}
              </span>
            )}
          </div>
        </div>

        {Icon && (
          <div className="p-2.5 rounded-xl bg-surface-alt border border-border/80 text-primary flex-shrink-0">
            <Icon className="w-5 h-5" />
          </div>
        )}
      </div>

      {(subtitle || trend) && (
        <div className="mt-3 pt-3 border-t border-border/60 flex items-center justify-between text-xs text-muted">
          {subtitle && <span>{subtitle}</span>}
          {trend && (
            <div className="flex items-center gap-1 font-mono text-[11px]">
              {trend.direction === 'up' && (
                <span className="text-success inline-flex items-center gap-0.5 font-medium">
                  <TrendingUp className="w-3.5 h-3.5" /> +{trend.value}
                </span>
              )}
              {trend.direction === 'down' && (
                <span className="text-danger inline-flex items-center gap-0.5 font-medium">
                  <TrendingDown className="w-3.5 h-3.5" /> -{trend.value}
                </span>
              )}
              {trend.direction === 'neutral' && (
                <span className="text-muted inline-flex items-center gap-0.5">
                  <Minus className="w-3.5 h-3.5" /> {trend.value}
                </span>
              )}
              {trend.label && <span className="text-muted/80 ml-1">{trend.label}</span>}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
