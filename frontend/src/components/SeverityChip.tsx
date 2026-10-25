import React from 'react';
import { getSeverityVocab, Severity } from '../lib/vocab';

interface SeverityChipProps {
  severity: Severity | string;
  showIcon?: boolean;
  className?: string;
}

export const SeverityChip: React.FC<SeverityChipProps> = ({
  severity,
  showIcon = true,
  className = '',
}) => {
  const vocab = getSeverityVocab(severity);
  const IconComponent = vocab.icon;

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono font-medium border ${vocab.badgeClass} ${className}`}
      title={vocab.description}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${vocab.dotClass}`} />
      {showIcon && <IconComponent className="w-3.5 h-3.5" />}
      <span>{vocab.label}</span>
    </span>
  );
};
