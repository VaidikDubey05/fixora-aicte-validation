import React from 'react';
import { getApplicationStateVocab, getVerificationStatusVocab } from '../lib/vocab';

interface StatusChipProps {
  status: string;
  type?: 'application' | 'verification';
  showIcon?: boolean;
  className?: string;
}

export const StatusChip: React.FC<StatusChipProps> = ({
  status,
  type = 'application',
  showIcon = true,
  className = '',
}) => {
  const vocab =
    type === 'verification'
      ? getVerificationStatusVocab(status)
      : getApplicationStateVocab(status);

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
