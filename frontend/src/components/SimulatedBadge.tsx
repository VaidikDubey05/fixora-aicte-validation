import React from 'react';
import { ExternalLink, Database } from 'lucide-react';

interface SimulatedBadgeProps {
  sourceName?: string;
  sourceUrl?: string;
  className?: string;
}

export const SimulatedBadge: React.FC<SimulatedBadgeProps> = ({
  sourceName = 'Simulated Statutory Registry',
  sourceUrl,
  className = '',
}) => {
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[11px] font-mono font-medium bg-surface-alt text-muted border border-border shadow-xs ${className}`}
      title="Mock integration cross-reference with statutory authority registry"
    >
      <Database className="w-3 h-3 text-secondary" />
      <span>Source: {sourceName}</span>
      <span className="text-[9px] uppercase px-1 py-0.2 rounded bg-secondary/15 text-secondary font-bold tracking-wider">
        SIMULATED SOURCE
      </span>
      {sourceUrl && (
        <a
          href={sourceUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="text-primary hover:underline inline-flex items-center"
        >
          <ExternalLink className="w-2.5 h-2.5 ml-0.5" />
        </a>
      )}
    </span>
  );
};
