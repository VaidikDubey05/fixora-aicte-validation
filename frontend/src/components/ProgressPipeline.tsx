import React, { useEffect } from 'react';
import {
  Upload,
  FileSearch,
  Cpu,
  CheckCircle2,
  GitCompare,
  ShieldAlert,
  ShieldCheck,
  Loader2,
  Check,
} from 'lucide-react';
import { usePipelineStatus } from '../api/usePipelineStatus';

export const PIPELINE_STAGES = [
  { id: 'Upload', label: 'Upload', icon: Upload, description: 'Statutory annexure ingestion & hashing' },
  { id: 'Classify', label: 'Classify', icon: FileSearch, description: 'Document category classification' },
  { id: 'Extract', label: 'Extract', icon: Cpu, description: 'OCR & metadata field extraction' },
  { id: 'Validate', label: 'Validate', icon: CheckCircle2, description: 'Deterministic APH rule evaluation' },
  { id: 'Cross-check', label: 'Cross-check', icon: GitCompare, description: 'Inter-document record consistency' },
  { id: 'Anomaly check', label: 'Anomaly check', icon: ShieldAlert, description: 'Preliminary anomaly indication' },
  { id: 'Verify', label: 'Verify', icon: ShieldCheck, description: 'External registry gateway reconciliation' },
];

interface ProgressPipelineProps {
  applicationId: string;
  compact?: boolean;
  className?: string;
  onComplete?: () => void;
  enabled?: boolean;
}

export const ProgressPipeline: React.FC<ProgressPipelineProps> = ({
  applicationId,
  compact = false,
  className = '',
  onComplete,
  enabled = true,
}) => {
  const { data: statusData, isLoading } = usePipelineStatus(applicationId, enabled);

  const rawStage = (statusData as any)?.current_stage || (statusData as any)?.stage || 'Upload';
  const progressPct = statusData?.progress_pct ?? (isLoading ? 10 : 100);
  const isRunning = (statusData as any)?.is_running ?? ((statusData as any)?.status === 'running' || (statusData as any)?.status === 'in_progress');

  // Determine current active stage index
  const stageIndex = PIPELINE_STAGES.findIndex(
    (s) => s.id.toLowerCase() === rawStage.toLowerCase() || s.label.toLowerCase() === rawStage.toLowerCase()
  );
  const currentIndex = stageIndex >= 0 ? stageIndex : isRunning ? 2 : PIPELINE_STAGES.length - 1;

  useEffect(() => {
    if (!isRunning && progressPct >= 100 && onComplete) {
      onComplete();
    }
  }, [isRunning, progressPct, onComplete]);

  if (compact) {
    return (
      <div className={`p-3 rounded-xl bg-surface border border-border text-xs shadow-xs ${className}`}>
        <div className="flex items-center justify-between gap-3 mb-2">
          <div className="flex items-center gap-2">
            {isRunning ? (
              <Loader2 className="w-3.5 h-3.5 text-primary animate-spin" />
            ) : (
              <Check className="w-3.5 h-3.5 text-success" />
            )}
            <span className="font-semibold text-text">
              {isRunning ? 'Validation Pipeline Running' : 'Validation Pipeline Completed'}
            </span>
            <span className="text-[10px] font-mono text-muted">
              ({rawStage})
            </span>
          </div>
          <span className="font-mono text-[11px] font-bold text-primary">
            {progressPct}%
          </span>
        </div>

        {/* Progress bar */}
        <div className="w-full bg-surface-alt h-1.5 rounded-full overflow-hidden border border-border/40">
          <div
            className="h-full bg-hero-gradient transition-all duration-500 rounded-full"
            style={{ width: `${progressPct}%` }}
          />
        </div>

        {/* Compact stage steps */}
        <div className="flex items-center justify-between gap-1 mt-2 overflow-x-auto pb-1 text-[10px] font-mono">
          {PIPELINE_STAGES.map((s, idx) => {
            const isDone = idx < currentIndex || (!isRunning && progressPct >= 100);
            const isCurrent = idx === currentIndex && isRunning;
            return (
              <div
                key={s.id}
                className={`flex items-center gap-1 px-1.5 py-0.5 rounded ${
                  isDone
                    ? 'text-success font-medium'
                    : isCurrent
                    ? 'text-primary font-bold bg-primary/10'
                    : 'text-muted'
                }`}
                title={s.description}
              >
                {isDone ? (
                  <Check className="w-2.5 h-2.5 text-success" />
                ) : isCurrent ? (
                  <Loader2 className="w-2.5 h-2.5 text-primary animate-spin" />
                ) : (
                  <span className="w-2 h-2 rounded-full bg-border" />
                )}
                <span className="hidden sm:inline truncate max-w-[65px]">{s.label}</span>
              </div>
            );
          })}
        </div>
      </div>
    );
  }

  return (
    <div className={`p-4 sm:p-6 rounded-2xl bg-surface border border-border shadow-card space-y-5 ${className}`}>
      {/* Header telemetry */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-border">
        <div className="space-y-0.5">
          <div className="flex items-center gap-2">
            <h4 className="text-sm font-bold font-heading text-text">
              Statutory Automated Validation Pipeline
            </h4>
            {isRunning ? (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-mono font-semibold bg-primary/15 text-primary border border-primary/30">
                <Loader2 className="w-3 h-3 animate-spin" /> RUNNING
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-mono font-semibold bg-success/15 text-success border border-success/30">
                <Check className="w-3 h-3" /> PIPELINE VERIFIED
              </span>
            )}
          </div>
          <p className="text-xs text-muted">
            Evaluating dossier against APH 2026-27 statutory rules, spatial constraints, and cross-registry hashes.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="text-right">
            <span className="text-[10px] font-mono uppercase text-muted block">Overall Progress</span>
            <span className="text-base font-bold font-mono text-primary">{progressPct}%</span>
          </div>
        </div>
      </div>

      {/* Main Multi-Stage Pipeline Stepper */}
      <div className="relative">
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2">
          {PIPELINE_STAGES.map((s, idx) => {
            const Icon = s.icon;
            const isDone = idx < currentIndex || (!isRunning && progressPct >= 100);
            const isCurrent = idx === currentIndex && isRunning;

            return (
              <div
                key={s.id}
                className={`p-3 rounded-xl border transition-all text-xs flex flex-col justify-between ${
                  isDone
                    ? 'border-success/30 bg-success/5 text-text'
                    : isCurrent
                    ? 'border-primary bg-primary/10 text-text ring-1 ring-primary/40 shadow-xs'
                    : 'border-border/60 bg-surface-alt/40 text-muted opacity-80'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <div
                    className={`w-7 h-7 rounded-lg flex items-center justify-center transition-colors ${
                      isDone
                        ? 'bg-success/20 text-success'
                        : isCurrent
                        ? 'bg-primary text-white shadow-glow'
                        : 'bg-surface border border-border text-muted'
                    }`}
                  >
                    {isDone ? (
                      <Check className="w-4 h-4 text-success" />
                    ) : isCurrent ? (
                      <Loader2 className="w-4 h-4 text-white animate-spin" />
                    ) : (
                      <Icon className="w-4 h-4" />
                    )}
                  </div>
                  <span className="font-mono text-[10px] text-muted font-bold">
                    0{idx + 1}
                  </span>
                </div>

                <div>
                  <h5
                    className={`font-semibold truncate text-xs ${
                      isDone ? 'text-success' : isCurrent ? 'text-primary' : 'text-text'
                    }`}
                  >
                    {s.label}
                  </h5>
                  <p className="text-[10px] text-muted line-clamp-2 mt-0.5 leading-tight">
                    {s.description}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
