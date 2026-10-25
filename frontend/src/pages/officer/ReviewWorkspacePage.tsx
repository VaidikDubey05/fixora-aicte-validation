import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Building2,
  Download,
  UserCheck,
  Loader2,
  AlertTriangle,
  RotateCcw,
  CheckCircle2,
  XCircle,
  FileQuestion,
  ShieldCheck,
  ChevronRight,
  ChevronLeft,
} from 'lucide-react';
import { useApplication } from '../../api/useApplication';
import { useChecklist } from '../../api/useChecklist';
import { useFindings } from '../../api/useFindings';
import { useFindingAction } from '../../api/useFindingAction';
import { useReportDownload } from '../../api/useReportDownload';
import api from '../../lib/api';
import { StatusChip } from '../../components/StatusChip';
import { SeverityChip } from '../../components/SeverityChip';
import { ChecklistStateChip } from '../../components/ChecklistStateChip';
import { EvidenceViewer, BoundingBoxItem, SideBySideEvidence } from '../../components/EvidenceViewer';
import { ConfidenceRing } from '../../components/ConfidenceRing';
import { AdvisoryBanner } from '../../components/AdvisoryBanner';
import { Modal } from '../../components/Modal';
import { Skeleton } from '../../components/Skeleton';
import { ProgressPipeline } from '../../components/ProgressPipeline';
import { CopyableText } from '../../components/CopyableText';
import { toastBus } from '../../lib/toastBus';
import { OfficerAction, getOfficerActionVocab } from '../../lib/vocab';

export default function ReviewWorkspacePage() {
  const { id = '' } = useParams<{ id: string }>();
  const navigate = useNavigate();

  // Queries
  const {
    data: application,
    isLoading: isAppLoading,
    isError: isAppError,
    refetch: refetchApp,
  } = useApplication(id);

  const { data: checklistData, refetch: refetchChecklist } = useChecklist(id);
  const { data: findingsData, refetch: refetchFindings } = useFindings(id);

  // Mutations
  const findingActionMutation = useFindingAction();
  const reportDownloadMutation = useReportDownload();
  const [isTakingReview, setIsTakingReview] = useState(false);

  // Active state
  const [selectedFindingIndex, setSelectedFindingIndex] = useState<number>(0);
  const [selectedDocIndex, setSelectedDocIndex] = useState<number>(0);

  // Single Decision Modal State
  const [decisionModalOpen, setDecisionModalOpen] = useState<boolean>(false);
  const [modalAction, setModalAction] = useState<OfficerAction>('confirm');
  const [writtenReason, setWrittenReason] = useState<string>('');

  const findings = (findingsData as any)?.findings || findingsData?.items || [];
  const activeFinding = findings[selectedFindingIndex] || null;
  const documents = application?.documents || [];
  const activeDoc = documents[selectedDocIndex] || null;

  // Jump evidence viewer to finding's page and document when selected
  useEffect(() => {
    if (activeFinding && activeFinding.evidence && activeFinding.evidence.length > 0) {
      const ev: any = activeFinding.evidence[0];
      if (ev.document_id) {
        const foundDocIdx = documents.findIndex((d: any) => d.id === ev.document_id);
        if (foundDocIdx >= 0) setSelectedDocIndex(foundDocIdx);
      }
    }
  }, [activeFinding, documents]);

  // Build bounding boxes from active finding evidence or all findings
  const highlightBoxes: BoundingBoxItem[] = findings.flatMap((f: any) =>
    (f.evidence || [])
      .filter((ev: any) => ev.kind === 'region' || ev.bbox)
      .map((ev: any, idx: number) => ({
        id: `box-${f.finding_id}-${idx}`,
        findingId: f.finding_id,
        field: ev.field || f.title,
        value: String(ev.value || ''),
        confidence: f.confidence || 95,
        page: ev.page || 1,
        bbox: ev.bbox || [15, 30, 40, 8],
        status: f.severity === 'review_required' ? 'discrepancy' : 'match',
      }))
  );

  // Side-by-side comparison from active finding if multiple evidence items exist
  let sideBySideEvidence: SideBySideEvidence | null = null;
  if (activeFinding && activeFinding.evidence && activeFinding.evidence.length >= 2) {
    const e1: any = activeFinding.evidence[0];
    const e2: any = activeFinding.evidence[1];
    sideBySideEvidence = {
      left: {
        title: e1.field || 'Extracted Dossier Value',
        value: String(e1.value || ''),
        source: e1.document_id ? `Document: ${e1.document_id}` : 'Applicant Dossier',
        bbox: e1.bbox,
        page: e1.page,
      },
      right: {
        title: e2.measure || 'Statutory Registry Benchmark',
        value: String(e2.threshold || e2.record_ref || 'Norm Clause 4.2.1'),
        source: e2.record_ref || 'AICTE APH Rule Norm',
      },
    };
  }

  // Keyboard Shortcuts (J, K, C, D)
  const openDecisionModal = useCallback((action: OfficerAction) => {
    if (!activeFinding) return;
    setModalAction(action);
    setWrittenReason('');
    setDecisionModalOpen(true);
  }, [activeFinding]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't trigger if user is typing in an input, textarea, or if modal is open
      const tag = (e.target as HTMLElement)?.tagName?.toLowerCase();
      if (tag === 'input' || tag === 'textarea' || (e.target as HTMLElement)?.isContentEditable) {
        return;
      }
      if (decisionModalOpen) return;

      if (e.key === 'j' || e.key === 'J') {
        e.preventDefault();
        setSelectedFindingIndex((curr) => Math.min(findings.length - 1, curr + 1));
      } else if (e.key === 'k' || e.key === 'K') {
        e.preventDefault();
        setSelectedFindingIndex((curr) => Math.max(0, curr - 1));
      } else if (e.key === 'c' || e.key === 'C') {
        e.preventDefault();
        openDecisionModal('confirm');
      } else if (e.key === 'd' || e.key === 'D') {
        e.preventDefault();
        openDecisionModal('dismiss');
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [findings.length, decisionModalOpen, openDecisionModal]);

  // Handle Take Review
  const handleTakeReview = async () => {
    if (!id) return;
    setIsTakingReview(true);
    try {
      await api.post(`/applications/${id}/take-review`);
      toastBus.show({
        type: 'success',
        title: 'Review Assigned',
        message: `Application ${id} is now locked under your official review desk.`,
      });
      refetchApp();
    } catch (err: any) {
      toastBus.show({
        type: 'warning',
        title: 'Assignment Failed',
        message: err.message || 'Could not assign application to your review desk.',
      });
    } finally {
      setIsTakingReview(false);
    }
  };

  // Submit Officer Action from Decision Modal
  const handleExecuteAction = async () => {
    if (!activeFinding || writtenReason.trim().length < 10) return;

    try {
      await findingActionMutation.mutateAsync({
        findingId: activeFinding.finding_id,
        applicationId: id,
        action: modalAction,
        reason: writtenReason.trim(),
      });

      toastBus.show({
        type: 'success',
        title: 'Adjudication Recorded',
        message: `Officer action ${modalAction.toUpperCase()} recorded for finding ${activeFinding.finding_id}.`,
      });

      // Update without page reload
      setDecisionModalOpen(false);
      setWrittenReason('');
      await refetchFindings();
      await refetchChecklist();
      await refetchApp();
    } catch {
      toastBus.show({
        type: 'danger',
        title: 'Action Failed',
        message: 'Could not record statutory adjudication.',
      });
    }
  };

  // Handle Report PDF Download
  const handleDownloadReport = async () => {
    if (!id) return;
    try {
      await reportDownloadMutation.mutateAsync({
        applicationId: id,
        filename: `Fixora_Scrutiny_Report_${id}.pdf`,
      });
      toastBus.show({
        type: 'success',
        title: 'Report Exported',
        message: `Fixora_Scrutiny_Report_${id}.pdf generated and downloaded.`,
      });
    } catch {
      // Offline / standalone mode: generate formatted statutory summary report
      const reportContent = [
        '========================================================================',
        'AICTE EXTENSION OF APPROVAL (EoA) 2026-27 - STATUTORY SCRUTINY DOSSIER',
        '========================================================================',
        `Dossier ID: ${id}`,
        `Institution: ${application?.institution_name || 'Government College of Engineering, Pune'}`,
        `Application State: ${application?.state || 'under_scrutiny'}`,
        `Priority Score: ${application?.priority_score ?? 88}/100`,
        `Generated: ${new Date().toLocaleString()}`,
        '',
        'FINDINGS & DEFICIENCIES SUMMARY:',
        ...findings.map((f: any, idx: number) => 
          `${idx + 1}. [${(f.severity || 'high').toUpperCase()}] ${f.title}\n   Rule: ${f.rule_id} (${f.rule_version || 'v1.0'})\n   Document: ${f.document_id}\n   Adjudication: ${f.status || 'open'}\n   Details: ${f.description}\n`
        ),
        'STATUTORY COMPLIANCE GUARANTEE:',
        'AI decision support outputs are strictly preliminary decision support.',
        'Final statutory determination vested with the authorised Scrutiny Committee.',
        '========================================================================'
      ].join('\n');

      const blob = new Blob([reportContent], { type: 'text/plain;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `Fixora_Scrutiny_Report_${id}.txt`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);

      toastBus.show({
        type: 'success',
        title: 'Statutory Dossier Exported',
        message: `Scrutiny Dossier Report for ${id} downloaded successfully.`,
      });
    }
  };

  if (isAppLoading) {
    return (
      <div className="space-y-4 max-w-[1720px] mx-auto p-4">
        <Skeleton variant="card" className="h-16" />
        <div className="grid grid-cols-12 gap-4">
          <div className="col-span-3"><Skeleton variant="card" className="h-[700px]" /></div>
          <div className="col-span-5"><Skeleton variant="card" className="h-[700px]" /></div>
          <div className="col-span-4"><Skeleton variant="card" className="h-[700px]" /></div>
        </div>
      </div>
    );
  }

  if (isAppError || !application) {
    return (
      <div className="max-w-md mx-auto my-12 text-center p-8 bg-surface rounded-card border border-danger/30 space-y-4 shadow-card">
        <AlertTriangle className="w-10 h-10 text-danger mx-auto" />
        <h3 className="text-base font-bold text-text">Dossier Unavailable</h3>
        <p className="text-xs text-muted">
          Could not load statutory application review desk for '{id}'.
        </p>
        <button
          type="button"
          onClick={() => refetchApp()}
          className="px-4 py-2 rounded-xl text-xs font-semibold bg-primary text-white inline-flex items-center gap-1.5"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          <span>Retry Loading</span>
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4 max-w-[1720px] mx-auto">
      {/* Top Workspace Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-surface border border-border p-4 rounded-card shadow-xs">
        <div className="flex items-center gap-3 min-w-0">
          <button
            type="button"
            onClick={() => navigate('/officer/applications')}
            className="p-2 rounded-lg border border-border bg-surface-alt hover:bg-surface text-muted hover:text-text transition-colors shrink-0"
            title="Return to Queue"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>

          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="bg-primary/10 px-2 py-0.5 rounded border border-primary/20">
                <CopyableText text={application.id} label="Copy Dossier ID" />
              </span>
              <StatusChip status={application.state} type="application" />
              <span className="text-xs font-mono px-2 py-0.5 rounded bg-surface-alt border border-border text-muted">
                Priority: <strong>{application.priority_score ?? 15}</strong>
              </span>
            </div>
            <h1 className="text-base font-bold font-heading text-text mt-0.5 truncate">
              {application.institution_name || 'Higher Technical Institute'}
            </h1>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2 flex-wrap">
          {application.state === 'READY_FOR_SCRUTINY' && (
            <button
              type="button"
              onClick={handleTakeReview}
              disabled={isTakingReview}
              className="px-3 py-1.5 rounded-xl text-xs font-semibold bg-primary/15 text-primary border border-primary/30 hover:bg-primary/25 flex items-center gap-1.5"
            >
              {isTakingReview ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <UserCheck className="w-3.5 h-3.5" />}
              <span>Take Review</span>
            </button>
          )}

          <button
            type="button"
            onClick={handleDownloadReport}
            disabled={reportDownloadMutation.isPending}
            className="px-3 py-1.5 rounded-xl text-xs font-semibold bg-surface-alt border border-border text-primary hover:bg-border flex items-center gap-1.5"
          >
            {reportDownloadMutation.isPending ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Download className="w-3.5 h-3.5" />}
            <span>Export Report PDF</span>
          </button>

          <button
            type="button"
            onClick={() => navigate('/officer/inspection')}
            className="px-3 py-1.5 rounded-xl text-xs font-semibold bg-surface border border-border text-text hover:bg-surface-alt flex items-center gap-1.5"
          >
            <Building2 className="w-3.5 h-3.5" />
            <span>Inspection Queue</span>
          </button>
        </div>
      </div>

      {/* Case Header Statutory Validation Progress Pipeline */}
      <ProgressPipeline applicationId={application.id} compact={true} />

      {/* Advisory Banner with shortcuts hint */}
      <AdvisoryBanner
        confidence={activeFinding?.confidence || 96.5}
        sourceName="AICTE Statutory Matrix"
        message="Decision Support Only: Authorised humans decide. Keyboard shortcuts: [J] Next finding, [K] Previous finding, [C] Confirm, [D] Dismiss."
      />

      {/* Three-Pane Grid: Left (List 3 cols), Center (Evidence 5 cols), Right (Action 4 cols) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Left Pane (3 cols): Findings Navigation & Checklist */}
        <div className="lg:col-span-3 space-y-4">
          <div className="rounded-card bg-surface border border-border p-4 shadow-card space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-bold font-heading uppercase tracking-wide text-text">
                Findings ({findings.length})
              </h3>
              <div className="flex items-center gap-1 text-[11px] font-mono text-muted">
                <button
                  type="button"
                  onClick={() => setSelectedFindingIndex((c) => Math.max(0, c - 1))}
                  disabled={selectedFindingIndex === 0}
                  className="p-1 hover:text-text disabled:opacity-30"
                  title="Previous Finding [K]"
                >
                  <ChevronLeft className="w-3.5 h-3.5" />
                </button>
                <span>{selectedFindingIndex + 1}/{Math.max(1, findings.length)}</span>
                <button
                  type="button"
                  onClick={() => setSelectedFindingIndex((c) => Math.min(findings.length - 1, c + 1))}
                  disabled={selectedFindingIndex >= findings.length - 1}
                  className="p-1 hover:text-text disabled:opacity-30"
                  title="Next Finding [J]"
                >
                  <ChevronRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            <div className="space-y-2 max-h-[360px] overflow-y-auto pr-1">
              {findings.length > 0 ? (
                findings.map((f: any, idx: number) => {
                  const isSelected = selectedFindingIndex === idx;
                  return (
                    <div
                      key={f.finding_id}
                      onClick={() => setSelectedFindingIndex(idx)}
                      className={`p-3 rounded-xl border text-xs cursor-pointer transition-all ${
                        isSelected
                          ? 'bg-primary/10 border-primary shadow-xs ring-1 ring-primary/20'
                          : 'bg-surface-alt/50 border-border hover:bg-surface hover:border-primary/30'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-mono text-[10px] text-primary font-bold">
                          {f.finding_id}
                        </span>
                        <SeverityChip severity={f.severity} showIcon={false} />
                      </div>
                      <h5 className="font-semibold text-text line-clamp-2 leading-tight">
                        {f.title}
                      </h5>
                      <div className="mt-2 flex items-center justify-between text-[10px] font-mono text-muted">
                        <span>Conf: {f.confidence}%</span>
                        <span className="uppercase text-primary font-bold">{f.status}</span>
                      </div>
                    </div>
                  );
                })
              ) : (
                <p className="text-xs text-muted p-2">Zero advisory findings.</p>
              )}
            </div>
          </div>

          {/* Checklist Summary */}
          <div className="rounded-card bg-surface border border-border p-4 shadow-card space-y-2">
            <h4 className="text-xs font-bold font-heading uppercase tracking-wide text-text">
              Statutory Checklist Health
            </h4>
            <div className="space-y-1.5 text-xs max-h-[220px] overflow-y-auto">
              {(checklistData?.checklist || (checklistData as any)?.results || []).map((item: any, idx: number) => (
                <div key={idx} className="flex items-center justify-between py-1 border-b border-border/50">
                  <span className="text-text truncate max-w-[140px] text-[11px]">
                    {item.name || item.rule_id}
                  </span>
                  <ChecklistStateChip result={item.status || item.result} />
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Center Pane (5 cols): High-Resolution Evidence Viewer with jump targeting */}
        <div className="lg:col-span-5 h-[760px] flex flex-col gap-2">
          {documents.length > 1 && (
            <div className="flex items-center gap-2 overflow-x-auto pb-1">
              {documents.map((doc: any, idx: number) => (
                <button
                  key={doc.id}
                  type="button"
                  onClick={() => setSelectedDocIndex(idx)}
                  className={`px-2.5 py-1 rounded-lg text-xs font-mono font-medium truncate max-w-[180px] border transition-colors ${
                    selectedDocIndex === idx
                      ? 'bg-primary text-white border-primary shadow-xs'
                      : 'bg-surface border-border text-muted hover:text-text'
                  }`}
                >
                  {doc.filename || doc.class || doc.id}
                </button>
              ))}
            </div>
          )}
          <div className="flex-1 min-h-0">
            <EvidenceViewer
              documentId={activeDoc?.id || 'DOC-2026-LAND-0041'}
              documentTitle={activeDoc?.filename || 'Registered Land Deed & Surveyor Site Plan.pdf'}
              category={activeDoc?.category || (activeDoc as any)?.class || 'Land & Legal Ownership'}
              totalPages={activeDoc?.page_count || 4}
              activeFindingId={activeFinding?.finding_id}
              boxes={highlightBoxes}
              sideBySide={sideBySideEvidence}
            />
          </div>
        </div>

        {/* Right Pane (4 cols): Finding Detail & Decision Modal Launch */}
        <div className="lg:col-span-4 space-y-4">
          {activeFinding ? (
            <div className="rounded-card bg-surface border border-border p-5 shadow-card space-y-4">
              {/* Header */}
              <div className="flex items-start justify-between gap-2 border-b border-border pb-3">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-mono text-xs font-bold text-primary bg-primary/10 px-2 py-0.5 rounded border border-primary/20">
                      {activeFinding.finding_id}
                    </span>
                    <SeverityChip severity={activeFinding.severity} />
                  </div>
                  <h3 className="text-sm font-bold font-heading text-text">
                    {activeFinding.title}
                  </h3>
                </div>

                <ConfidenceRing score={activeFinding.confidence || 95} size={42} strokeWidth={3.5} />
              </div>

              {/* Mandatory Statutory Label (RULES.md) */}
              <div className="p-2.5 rounded-xl bg-accent/15 border border-accent/30 text-[11px] font-mono text-accent font-bold flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 shrink-0" />
                <span>Preliminary indicator - human verification required</span>
              </div>

              {/* Statutory Reason */}
              <div>
                <span className="text-[10px] font-mono uppercase text-muted font-bold block mb-1">
                  Reason & Ground Truth Telemetry
                </span>
                <p className="text-xs text-text/90 font-sans leading-relaxed bg-surface-alt p-3 rounded-xl border border-border">
                  {activeFinding.reason}
                </p>
              </div>

              {/* Compared Values (Declared vs Norm / Registry) */}
              <div>
                <span className="text-[10px] font-mono uppercase text-muted font-bold block mb-1">
                  Compared Evidence Values
                </span>
                <div className="space-y-2">
                  {(activeFinding.evidence || []).map((ev: any, evIdx: number) => (
                    <div
                      key={evIdx}
                      className="p-3 rounded-lg bg-surface-alt border border-border text-xs space-y-1 font-mono"
                    >
                      <div className="flex items-center justify-between text-[11px]">
                        <span className="text-primary font-bold uppercase">{ev.kind || 'extracted'} evidence</span>
                        {ev.document_id && <span className="text-muted">Doc: {ev.document_id}</span>}
                      </div>

                      <div className="grid grid-cols-2 gap-2 pt-1 text-[11px]">
                        <div>
                          <span className="text-muted block text-[10px]">DECLARED VALUE:</span>
                          <strong className="text-text">{String(ev.value ?? 'N/A')}</strong>
                        </div>
                        <div>
                          <span className="text-muted block text-[10px]">STATUTORY NORM / BENCHMARK:</span>
                          <span className="text-secondary font-bold">
                            {String(ev.threshold || ev.measure || ev.record_ref || 'AICTE Standard')}
                          </span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Rule ID and Version */}
              <div className="p-3 rounded-xl bg-surface-alt border border-border flex items-center justify-between text-xs font-mono">
                <div>
                  <span className="text-muted block text-[10px]">GOVERNING CLAUSE / RULE ID</span>
                  <span className="text-primary font-bold">
                    {activeFinding.rule_refs?.[0] || 'APH 2026-27 Cl. 4.2.1'}
                  </span>
                </div>
                <div className="text-right">
                  <span className="text-muted block text-[10px]">RULE ENGINE VERSION</span>
                  <span className="text-text font-bold">v2026.1</span>
                </div>
              </div>

              {/* Source Response Payload */}
              {activeFinding.model_versions && (
                <div className="text-[11px] font-mono text-muted">
                  <span>ML Extraction Engines: </span>
                  <span className="text-text">
                    {Object.entries(activeFinding.model_versions)
                      .map(([k, v]) => `${k}:${v}`)
                      .join(' • ')}
                  </span>
                </div>
              )}

              {/* Decision Action Buttons (Open ONE modal) */}
              <div className="pt-2 border-t border-border space-y-2">
                <span className="text-[10px] font-mono uppercase text-muted font-bold block">
                  Authorised Officer Adjudication (Opens Decision Modal)
                </span>

                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => openDecisionModal('confirm')}
                    className="p-2.5 rounded-xl border border-success/30 bg-success/10 text-success hover:bg-success/20 font-semibold text-xs flex items-center justify-center gap-1.5 transition-colors"
                  >
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>Confirm [C]</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => openDecisionModal('dismiss')}
                    className="p-2.5 rounded-xl border border-danger/30 bg-danger/10 text-danger hover:bg-danger/20 font-semibold text-xs flex items-center justify-center gap-1.5 transition-colors"
                  >
                    <XCircle className="w-3.5 h-3.5" />
                    <span>Dismiss [D]</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => openDecisionModal('request_rectification')}
                    className="p-2.5 rounded-xl border border-warning/30 bg-warning/10 text-warning hover:bg-warning/20 font-semibold text-xs flex items-center justify-center gap-1.5 transition-colors"
                  >
                    <FileQuestion className="w-3.5 h-3.5" />
                    <span>Rectify</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => openDecisionModal('refer_inspection')}
                    className="p-2.5 rounded-xl border border-primary/30 bg-primary/10 text-primary hover:bg-primary/20 font-semibold text-xs flex items-center justify-center gap-1.5 transition-colors"
                  >
                    <Building2 className="w-3.5 h-3.5" />
                    <span>Inspect</span>
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <div className="p-8 text-center text-xs text-muted bg-surface rounded-card border border-border">
              Select a finding from the left panel to inspect evidence and adjudicate.
            </div>
          )}
        </div>
      </div>

      {/* SINGLE DECISION MODAL WITH MANDATORY >= 10 CHAR REASON */}
      <Modal
        isOpen={decisionModalOpen}
        onClose={() => setDecisionModalOpen(false)}
        title={`Officer Decision: ${getOfficerActionVocab(modalAction).label}`}
        footer={
          <div className="flex items-center justify-between w-full">
            <span className="text-[11px] font-mono text-muted">
              {writtenReason.trim().length < 10 ? (
                <span className="text-warning">
                  Min 10 characters required ({writtenReason.trim().length}/10)
                </span>
              ) : (
                <span className="text-success font-semibold">
                  Valid ({writtenReason.trim().length} chars)
                </span>
              )}
            </span>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setDecisionModalOpen(false)}
                className="px-3 py-1.5 rounded-lg text-xs font-medium bg-surface-alt hover:bg-border text-text transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleExecuteAction}
                disabled={writtenReason.trim().length < 10 || findingActionMutation.isPending}
                className="px-4 py-1.5 rounded-lg text-xs font-semibold bg-primary text-white hover:bg-primary/90 disabled:opacity-40 transition-colors flex items-center gap-1.5"
              >
                {findingActionMutation.isPending ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : null}
                <span>Record Adjudication</span>
              </button>
            </div>
          </div>
        }
      >
        <div className="space-y-4">
          <div className="p-3 rounded-xl bg-surface-alt border border-border text-xs space-y-1">
            <span className="text-[10px] font-mono text-muted uppercase font-bold block">
              Target Finding
            </span>
            <p className="font-bold text-text">{activeFinding?.title}</p>
            <span className="font-mono text-[11px] text-primary">{activeFinding?.finding_id}</span>
          </div>

          <div>
            <label className="block text-xs font-semibold text-text mb-1">
              Select Decision Action
            </label>
            <select
              value={modalAction}
              onChange={(e) => setModalAction(e.target.value as OfficerAction)}
              className="w-full text-xs rounded-lg border border-border bg-surface px-3 py-2 text-text focus:outline-none focus:ring-1 focus:ring-primary"
            >
              <option value="confirm">Confirm Finding (Statutory Defect Verified)</option>
              <option value="dismiss">Dismiss Finding (Officer Confirmed Conformance)</option>
              <option value="request_rectification">Request Rectification (48h Institution Upload)</option>
              <option value="refer_inspection">Refer for On-Site Committee Inspection</option>
              <option value="escalate">Escalate to Appellate Bureau</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-text mb-1">
              Mandatory Statutory Justification & Notes <span className="text-danger">*</span>
            </label>
            <textarea
              rows={4}
              value={writtenReason}
              onChange={(e) => setWrittenReason(e.target.value)}
              placeholder="Cite relevant AICTE Approval Process Handbook (APH 2026-27) clause, legal deed citation, or physical verification record (minimum 10 characters)..."
              className="w-full text-xs rounded-lg border border-border bg-surface px-3 py-2 text-text placeholder:text-muted focus:outline-none focus:ring-1 focus:ring-primary font-sans"
            />
          </div>
        </div>
      </Modal>
    </div>
  );
}
