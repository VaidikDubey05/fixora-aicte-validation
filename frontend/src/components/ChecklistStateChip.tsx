import React from 'react';
import { getChecklistResultVocab, ChecklistResult } from '../lib/vocab';

interface ChecklistStateChipProps {
  result: ChecklistResult | string;
  showIcon?: boolean;
  className?: string;
}

export const ChecklistStateChip: React.FC<ChecklistStateChipProps> = ({
  result,
  showIcon = true,
  className = '',
}) => {
  const vocab = getChecklistResultVocab(result);
  const IconComponent = vocab.icon;

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono font-medium border ${vocab.badgeClass} ${className}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${vocab.dotClass}`} />
      {showIcon && <IconComponent className="w-3.5 h-3.5" />}
      <span>{vocab.label}</span>
    </span>
  );
};
