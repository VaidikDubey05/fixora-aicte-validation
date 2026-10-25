import React, { useState } from 'react';
import {
  AlertCircle,
  Layers,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import {
  FindingType,
  Severity,
  OfficerAction,
  getFindingTypeVocab,
  getOfficerActionVocab,
} from '../lib/vocab';
import { SeverityChip } from './SeverityChip';
import { ConfidenceRing } from './ConfidenceRing';
import { AdvisoryBanner } from './AdvisoryBanner';

export interface EvidenceItem {
  kind: 'region' | 'record' | 'metadata' | 'source' | 'rule';
  document_id?: string;
  page?: number;
  bbox?: [number, number, number, number];
  field?: string;
  value?: string | number;
  measure?: string;
  threshold?: string | number;
  record_ref?: string;
}

export interface Finding {
  finding_id: string;
  application_id: string;
  type: FindingType;
  severity: Severity;
  title: string;
  reason: string;
  evidence: EvidenceItem[];
  rule_refs: string[];
  confidence: number;
  label?: string;
  status: 'open' | 'confirmed' | 'dismissed' | 'rectification_requested' | 'escalated';
  model_versions?: Record<string, string>;
  created_at?: string;
}

interface FindingPanelProps {
  finding: Finding;
  onAction?: (action: OfficerAction, writtenReason: string) => void;
  isOfficer?: boolean;
  className?: string;
}

export const FindingPanel: React.FC<FindingPanelProps> = ({
  finding,
  onAction,
  isOfficer = true,
  className = '',
}) => {
  const [selectedAction, setSelectedAction] = useState<OfficerAction | null>(null);
  const [writtenReason, setWrittenReason] = useState<string>('');
  const [errorMsg, setErrorMsg] = useState<string>('');
  const [isEvidenceExpanded, setIsEvidenceExpanded] = useState<boolean>(true);

  const typeVocab = getFindingTypeVocab(finding.type);
  const isAnomaly = finding.type === 'possible_anomaly';

  const handleExecuteAction = () => {
    if (!selectedAction) return;
    if (!writtenReason.trim()) {
      setErrorMsg('A written statutory justification is mandatory for officer action.');
      return;
    }
    setErrorMsg('');
    if (onAction) {
      onAction(selectedAction, writtenReason.trim());
    }
  };

  return (
    <div className={`rounded-card bg-surface border border-border p-6 shadow-card space-y-5 ${className}`}>
      {/* Header with IDs and Chips */}
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3 pb-4 border-b border-border">
        <div>
          <div className="flex flex-wrap items-center gap-2 mb-1.5">
            <span className="font-mono text-xs font-semibold text-primary bg-primary/10 px-2 py-0.5 rounded border border-primary/20">
              {finding.finding_id}
            </span>
            <SeverityChip severity={finding.severity} />
            <span className="text-xs font-mono px-2 py-0.5 rounded-full border border-border bg-surface-alt text-muted">
              {typeVocab.label}
            </span>
          </div>
          <h3 className="text-base font-bold font-heading text-text">
            {finding.title}
          </h3>
        </div>

        <div className="flex items-center gap-2 self-start sm:self-center">
          <ConfidenceRing score={finding.confidence} size={42} strokeWidth={3.5} />
        </div>
      </div>

      {/* Advisory Banner */}
      <AdvisoryBanner
        confidence={finding.confidence}
        message={finding.reason}
        isPreliminaryIndicator={isAnomaly}
      />

      {/* Evidence Breakdown */}
      <div className="rounded-xl border border-border bg-surface-alt/30 overflow-hidden">
        <button
          type="button"
          onClick={() => setIsEvidenceExpanded(!isEvidenceExpanded)}
          className="w-full px-4 py-3 bg-surface-alt/60 flex items-center justify-between text-left font-sans text-xs font-bold text-text hover:bg-surface-alt transition-colors"
        >
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-primary" />
            <span>Documentary Evidence ({finding.evidence.length} points)</span>
          </div>
          {isEvidenceExpanded ? (
            <ChevronUp className="w-4 h-4 text-muted" />
          ) : (
            <ChevronDown className="w-4 h-4 text-muted" />
          )}
        </button>

        {isEvidenceExpanded && (
          <div className="p-4 space-y-3">
            {finding.evidence.map((ev, index) => (
              <div
                key={index}
                className="p-3 rounded-lg bg-surface border border-border text-xs space-y-1.5 shadow-xs"
              >
                <div className="flex items-center justify-between font-mono text-[11px]">
                  <span className="text-primary font-semibold uppercase">{ev.kind} evidence</span>
                  {ev.document_id && (
                    <span className="text-muted">
                      Doc: {ev.document_id} {ev.page ? `(p. ${ev.page})` : ''}
                    </span>
                  )}
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1 font-mono text-[11px]">
                  {ev.field && (
                    <div>
                      <span className="text-muted block text-[10px]">EXTRACTED FIELD:</span>
                      <strong className="text-text">{ev.field}</strong>
                    </div>
                  )}
                  {ev.value !== undefined && (
                    <div>
                      <span className="text-muted block text-[10px]">DECLARED VALUE:</span>
                      <strong className="text-text">{String(ev.value)}</strong>
                    </div>
                  )}
                  {ev.threshold !== undefined && (
                    <div>
                      <span className="text-muted block text-[10px]">APH STATUTORY NORM:</span>
                      <span className="text-secondary font-bold">{String(ev.threshold)}</span>
                    </div>
                  )}
                  {ev.record_ref && (
                    <div>
                      <span className="text-muted block text-[10px]">REGISTRY RECORD REF:</span>
                      <span className="text-muted">{ev.record_ref}</span>
                    </div>
                  )}
                </div>
              </div>
            ))}

            {finding.rule_refs && finding.rule_refs.length > 0 && (
              <div className="pt-2 flex flex-wrap items-center gap-1.5 text-[11px] font-mono text-muted">
                <span>Governing Norm Clauses:</span>
                {finding.rule_refs.map((ref) => (
                  <span
                    key={ref}
                    className="px-2 py-0.5 rounded bg-surface border border-border text-primary font-semibold"
                  >
                    {ref}
                  </span>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Authorised Scrutiny Officer Adjudication Deck */}
      {isOfficer && (
        <div className="rounded-xl border border-primary/20 bg-surface-alt/40 p-4 space-y-4">
          <div className="flex items-center justify-between">
            <h4 className="text-xs font-bold font-heading uppercase tracking-wide text-text">
              Officer Adjudication Protocol
            </h4>
            <span className="text-[10px] font-mono text-muted">Mandatory Written Reason</span>
          </div>

          {/* Action Choice Buttons */}
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
            {(
              [
                'confirm',
                'dismiss',
                'request_rectification',
                'refer_inspection',
                'escalate',
              ] as OfficerAction[]
            ).map((act) => {
              const actVocab = getOfficerActionVocab(act);
              const isSelected = selectedAction === act;
              const Icon = actVocab.icon;

              return (
                <button
                  key={act}
                  type="button"
                  onClick={() => {
                    setSelectedAction(act);
                    setErrorMsg('');
                  }}
                  className={`flex flex-col items-center justify-center gap-1.5 p-2.5 rounded-xl border text-center transition-all ${
                    isSelected
                      ? 'bg-hero-gradient text-white border-primary shadow-glow ring-2 ring-primary/20'
                      : 'bg-surface text-text border-border hover:border-primary/40 hover:bg-surface-alt'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  <span className="text-[11px] font-semibold leading-tight font-sans">
                    {actVocab.label}
                  </span>
                </button>
              );
            })}
          </div>

          {selectedAction && (
            <div className="space-y-3 pt-2">
              <label className="block text-xs font-medium text-text">
                Statutory Reason for <strong className="text-primary">{getOfficerActionVocab(selectedAction).label}</strong>:
              </label>
              <textarea
                value={writtenReason}
                onChange={(e) => {
                  setWrittenReason(e.target.value);
                  if (errorMsg) setErrorMsg('');
                }}
                rows={3}
                placeholder="Enter formal statutory justification citing relevant AICTE Approval Process Handbook clause or submitted verification affidavit..."
                className="w-full rounded-xl border border-border bg-surface p-3 text-xs text-text placeholder:text-muted focus:border-primary focus:ring-2 focus:ring-primary/20 outline-none font-sans"
              />

              {errorMsg && (
                <div className="flex items-center gap-1.5 text-xs text-danger font-medium">
                  <AlertCircle className="w-4 h-4" />
                  <span>{errorMsg}</span>
                </div>
              )}

              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => {
                    setSelectedAction(null);
                    setWrittenReason('');
                    setErrorMsg('');
                  }}
                  className="px-3 py-1.5 text-xs font-medium rounded-lg text-muted hover:text-text"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleExecuteAction}
                  className="px-4 py-2 rounded-xl text-xs font-semibold bg-hero-gradient text-white shadow-glow hover:brightness-105 active:scale-95 transition-all"
                >
                  Record Statutory Adjudication
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
