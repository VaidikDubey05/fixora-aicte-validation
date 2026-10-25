import React, { useState } from 'react';
import { Copy, Check } from 'lucide-react';

interface CopyableTextProps {
  text: string;
  displayValue?: string;
  label?: string;
  className?: string;
}

export const CopyableText: React.FC<CopyableTextProps> = ({
  text,
  displayValue,
  label,
  className = '',
}) => {
  const [copied, setCopied] = useState<boolean>(false);

  const handleCopy = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!text) return;
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  };

  return (
    <button
      type="button"
      onClick={handleCopy}
      title={label || `Copy ${text}`}
      className={`inline-flex items-center gap-1.5 font-mono text-xs text-text hover:text-primary transition-colors group cursor-pointer ${className}`}
    >
      <span className="truncate">{displayValue || text}</span>
      {copied ? (
        <span className="inline-flex items-center gap-0.5 text-[10px] text-success font-semibold">
          <Check className="w-3 h-3 text-success animate-in zoom-in" />
          <span>Copied</span>
        </span>
      ) : (
        <Copy className="w-3 h-3 text-muted opacity-50 group-hover:opacity-100 group-hover:text-primary transition-opacity" />
      )}
    </button>
  );
};
