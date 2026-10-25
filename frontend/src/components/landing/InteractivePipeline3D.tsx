import React, { useState } from 'react';
import {
  Upload,
  Layers,
  FileSearch,
  CheckSquare,
  GitCompare,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  CheckCircle2,
} from 'lucide-react';

interface PipelineStage {
  id: string;
  number: number;
  name: string;
  shortDesc: string;
  icon: any;
  color: string;
  badge: string;
  details: {
    statutoryObjective: string;
    rulesEvaluated: string[];
    technicalOutput: string;
    sampleMetric: string;
  };
}

const PIPELINE_STAGES: PipelineStage[] = [
  {
    id: 'stage-1',
    number: 1,
    name: 'Intake & Security Quarantine',
    shortDesc: 'Antivirus scan, SHA-256 genesis hashing & PDF structure validation',
    icon: Upload,
    color: '#5B5BFF',
    badge: 'STAGE 1',
    details: {
      statutoryObjective: 'Ensure uploaded dossiers are sanitized, immutable, and digitally fingerprinted before processing.',
      rulesEvaluated: ['PDF/A-1b conformance check', 'MIME-type binary validation', 'SHA-256 genesis block creation'],
      technicalOutput: 'Immutable encrypted storage blob with initial audit ledger registration.',
      sampleMetric: '100% Malware-Free Guarantee',
    },
  },
  {
    id: 'stage-2',
    number: 2,
    name: 'Statutory Document Classification',
    shortDesc: 'Deep visual & layout classification into 9 mandatory AICTE document classes',
    icon: Layers,
    color: '#00D1C1',
    badge: 'STAGE 2',
    details: {
      statutoryObjective: 'Identify whether the uploaded annexure matches the required slot (e.g. Land Deed, Fire NOC, Occupancy).',
      rulesEvaluated: ['Layout geometry classification', 'Emblem and notary seal localization', 'Class boundary confidence >95%'],
      technicalOutput: 'Document class assignment with confidence index and page layout map.',
      sampleMetric: '99.2% Classification Accuracy',
    },
  },
  {
    id: 'stage-3',
    number: 3,
    name: 'High-Precision Field Extraction',
    shortDesc: 'OCR tokenization, coordinate mapping & statutory key-value extraction',
    icon: FileSearch,
    color: '#FFB800',
    badge: 'STAGE 3',
    details: {
      statutoryObjective: 'Extract critical parameters including land acreage, instructional areas, certificate numbers, and validity dates.',
      rulesEvaluated: ['Acreage & carpet area parser', 'Statutory expiry date normalizer', 'Authority and registrar entity extractor'],
      technicalOutput: 'Normalized JSON fields with exact bounding box coordinates (x0, y0, x1, y1).',
      sampleMetric: '100% Extraction Accuracy on Eval Suite',
    },
  },
  {
    id: 'stage-4',
    number: 4,
    name: 'APH Rule Pack Validation',
    shortDesc: 'Evaluating AICTE Approval Process Handbook (APH 2026-27) threshold rules',
    icon: CheckSquare,
    color: '#22C55E',
    badge: 'STAGE 4',
    details: {
      statutoryObjective: 'Verify institutional compliance against official norms (e.g. rural mega-campuses minimum 7.5 contiguous acres).',
      rulesEvaluated: ['RULE-APH-FIRE-01 (Fire NOC Validity)', 'RULE-APH-AREA-03 (Built-Up Norms)', 'RULE-APH-TER-01 (Processing Fee)'],
      technicalOutput: 'Compliance scorecard with pass/flag status and mandatory written reason requirement for officers.',
      sampleMetric: '35+ Statutory Rule Checks',
    },
  },
  {
    id: 'stage-5',
    number: 5,
    name: 'Cross-Document Reconciliation',
    shortDesc: 'Reconciling affidavit declarations against architectural floor plans & fee receipts',
    icon: GitCompare,
    color: '#2DA8FF',
    badge: 'STAGE 5',
    details: {
      statutoryObjective: 'Detect discrepancies between values declared in affidavits and third-party verified annexures.',
      rulesEvaluated: ['Affidavit vs Architect Blueprint area delta (<5% variance allowed)', 'TER receipt transaction UTR vs Bank Ledger'],
      technicalOutput: 'Discrepancy report with side-by-side evidence pairing for review workspace.',
      sampleMetric: '<5% Tolerance Threshold',
    },
  },
  {
    id: 'stage-6',
    number: 6,
    name: 'Forensic Anomaly Detection',
    shortDesc: 'Substrate compression analysis & seal consistency inspection',
    icon: ShieldAlert,
    color: '#FF4D6D',
    badge: 'STAGE 6',
    details: {
      statutoryObjective: 'Identify visual artifacts and stamp boundary compression gradients requiring officer inspection.',
      rulesEvaluated: ['RULE-FORENSIC-SEAL-02 (Notary stamp resolution)', 'Preliminary indicator tag generation'],
      technicalOutput: 'Advisory flag: "Preliminary indicator - human verification required" (no definitive automated rejection).',
      sampleMetric: '100% Precision on Altered Benchmarks',
    },
  },
  {
    id: 'stage-7',
    number: 7,
    name: 'External Registry Verification',
    shortDesc: 'Automated verification against State IGR, Fire Services & Central Gateways',
    icon: ShieldCheck,
    color: '#5B5BFF',
    badge: 'STAGE 7',
    details: {
      statutoryObjective: 'Confirm statutory validity directly with issuing authorities via live integration APIs.',
      rulesEvaluated: ['State IGR Land Registration match', 'Municipal Fire Safety Bureau NOC lookup', 'Central Banking UTR verification'],
      technicalOutput: 'Cryptographically signed verification certificate with external transaction ID.',
      sampleMetric: 'Instant Gateway Adjudication',
    },
  },
];

export const InteractivePipeline3D: React.FC = () => {
  const [activeStageIndex, setActiveStageIndex] = useState<number>(3); // Default to APH Rule Validation
  const activeStage = PIPELINE_STAGES[activeStageIndex];
  const Icon = activeStage.icon;

  return (
    <div className="w-full max-w-6xl mx-auto space-y-8">
      {/* Interactive Step Rail */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
        {PIPELINE_STAGES.map((stage, idx) => {
          const isSelected = idx === activeStageIndex;
          const StageIcon = stage.icon;

          return (
            <button
              key={stage.id}
              type="button"
              onClick={() => setActiveStageIndex(idx)}
              className={`p-3.5 rounded-2xl border text-left transition-all duration-200 flex flex-col justify-between h-32 relative group overflow-hidden ${
                isSelected
                  ? 'bg-surface border-primary shadow-glow ring-2 ring-primary/30 translate-y-[-4px]'
                  : 'bg-surface/70 border-border hover:bg-surface hover:border-primary/40 hover:translate-y-[-2px]'
              }`}
            >
              {/* Top Row: Number & Icon */}
              <div className="flex items-center justify-between w-full">
                <span
                  className={`w-6 h-6 rounded-lg text-xs font-mono font-bold flex items-center justify-center ${
                    isSelected ? 'bg-primary text-white' : 'bg-surface-alt text-muted'
                  }`}
                >
                  {stage.number}
                </span>
                <StageIcon
                  className="w-4 h-4 transition-transform group-hover:scale-110"
                  style={{ color: stage.color }}
                />
              </div>

              {/* Bottom: Title */}
              <div>
                <p className="text-[10px] font-mono text-muted uppercase font-bold tracking-wider">
                  Stage {stage.number}
                </p>
                <h5 className="text-xs font-bold font-heading text-text leading-tight line-clamp-2 mt-0.5">
                  {stage.name}
                </h5>
              </div>

              {/* Active Bottom Glow Indicator */}
              {isSelected && (
                <div
                  className="absolute bottom-0 left-0 right-0 h-1"
                  style={{ backgroundColor: stage.color }}
                />
              )}
            </button>
          );
        })}
      </div>

      {/* Selected Stage Deep-Dive Card */}
      <div className="bg-surface border border-border rounded-3xl p-6 sm:p-8 shadow-card grid grid-cols-1 lg:grid-cols-12 gap-8 items-center relative overflow-hidden">
        {/* Ambient Corner Accent */}
        <div
          className="absolute top-0 right-0 w-80 h-80 rounded-full blur-3xl opacity-15 pointer-events-none"
          style={{ backgroundColor: activeStage.color }}
        />

        {/* Left Column: Stage Overview & Metric */}
        <div className="lg:col-span-5 space-y-4">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-xl text-xs font-mono font-bold bg-primary/10 text-primary border border-primary/20">
            <Sparkles className="w-3.5 h-3.5" />
            <span>{activeStage.badge} EXECUTION DECK</span>
          </div>

          <div className="flex items-center gap-3">
            <div
              className="w-12 h-12 rounded-2xl flex items-center justify-center text-white shadow-md"
              style={{ backgroundColor: activeStage.color }}
            >
              <Icon className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-xl font-bold font-heading text-text">
                {activeStage.name}
              </h3>
              <p className="text-xs text-muted font-sans mt-0.5">
                {activeStage.shortDesc}
              </p>
            </div>
          </div>

          <p className="text-xs text-text/90 font-sans leading-relaxed pt-1">
            {activeStage.details.statutoryObjective}
          </p>

          <div className="p-3.5 rounded-2xl bg-surface-alt border border-border flex items-center justify-between">
            <div>
              <span className="text-[10px] font-mono uppercase text-muted block font-bold">
                BENCHMARK METRIC
              </span>
              <span className="text-sm font-bold font-heading text-text">
                {activeStage.details.sampleMetric}
              </span>
            </div>
            <span className="px-2.5 py-1 rounded-xl bg-success/15 text-success border border-success/30 text-xs font-mono font-bold flex items-center gap-1">
              <CheckCircle2 className="w-3.5 h-3.5" /> VERIFIED
            </span>
          </div>
        </div>

        {/* Right Column: Rules & Technical Payload */}
        <div className="lg:col-span-7 bg-surface-alt/60 rounded-2xl border border-border p-5 sm:p-6 space-y-4">
          <div>
            <h4 className="text-xs font-mono font-bold uppercase tracking-wider text-primary flex items-center gap-1.5 mb-2.5">
              <span>Statutory Rule Checks</span>
            </h4>
            <div className="space-y-2">
              {activeStage.details.rulesEvaluated.map((rule, idx) => (
                <div
                  key={idx}
                  className="p-2.5 rounded-xl bg-surface border border-border text-xs font-sans text-text flex items-center gap-2.5 shadow-xs"
                >
                  <span className="w-5 h-5 rounded-md bg-primary/10 text-primary font-mono text-[10px] font-bold flex items-center justify-center shrink-0">
                    {idx + 1}
                  </span>
                  <span className="font-medium">{rule}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="pt-2 border-t border-border">
            <span className="text-[10px] font-mono text-muted uppercase font-bold block mb-1">
              Adjudication Output
            </span>
            <p className="text-xs font-mono text-text/85 bg-surface p-3 rounded-xl border border-border">
              {activeStage.details.technicalOutput}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
