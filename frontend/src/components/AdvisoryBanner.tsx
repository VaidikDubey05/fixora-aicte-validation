import React from 'react';
import { Sparkles, Info, ShieldAlert } from 'lucide-react';
import { SimulatedBadge } from './SimulatedBadge';

interface AdvisoryBannerProps {
  confidence?: number;
  sourceName?: string;
  message?: string;
  showDecisionSupportNotice?: boolean;
  isPreliminaryIndicator?: boolean;
  className?: string;
}

export const AdvisoryBanner: React.FC<AdvisoryBannerProps> = ({
  confidence = 94.2,
  sourceName = 'State Directorate of Technical Education Registry',
  message = 'Extracted data point differs from statutory benchmarks. Requires manual verification by an authorised scrutiny officer.',
  showDecisionSupportNotice = true,
  isPreliminaryIndicator = false,
  className = '',
}) => {
  return (
    <div
      className={`rounded-xl border-l-[3px] border-l-primary border border-border bg-surface/90 backdrop-blur-md p-3.5 shadow-xs transition-all ${className}`}
    >
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-border/60">
        <div className="flex items-center gap-2">
          <div className="p-1 rounded-md bg-primary/10 text-primary">
            {isPreliminaryIndicator ? (
              <ShieldAlert className="w-4 h-4 text-warning" />
            ) : (
              <Sparkles className="w-4 h-4" />
            )}
          </div>
          <span className="text-xs font-mono font-semibold text-text">
            {isPreliminaryIndicator
              ? `[Preliminary indicator - human verification required | Confidence ${confidence}%]`
              : `[AI Assistive Finding: Confidence Score ${confidence}%]`}
          </span>
        </div>
        {sourceName && <SimulatedBadge sourceName={sourceName} />}
      </div>

      <p className="mt-2 text-xs text-text/90 leading-relaxed font-sans">
        {message}
      </p>

      {showDecisionSupportNotice && (
        <div className="mt-2.5 pt-2 border-t border-border/40 flex items-center gap-1.5 text-[11px] text-muted">
          <Info className="w-3.5 h-3.5 flex-shrink-0 text-primary" />
          <span>
            <strong>Decision Support Only:</strong> System findings are advisory. No automated decision or rejection occurs without authorised human scrutiny.
          </span>
        </div>
      )}
    </div>
  );
};
