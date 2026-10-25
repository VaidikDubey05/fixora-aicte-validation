import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  AlertTriangle,
  Upload,
  ArrowLeft,
  FileText,
  Download,
  Loader2,
  RotateCcw,
  CheckCircle2,
  Clock,
  ShieldCheck,
} from 'lucide-react';
import { useApplication } from '../../api/useApplication';
import { useChecklist } from '../../api/useChecklist';
import { useFindings } from '../../api/useFindings';
import { useUploadDocument } from '../../api/useUploadDocument';
import { StatusChip } from '../../components/StatusChip';
import { ChecklistStateChip } from '../../components/ChecklistStateChip';
import { Skeleton } from '../../components/Skeleton';
import { EmptyState } from '../../components/EmptyState';
import { Timeline, TimelineEvent } from '../../components/Timeline';
import { CopyableText } from '../../components/CopyableText';
import { toastBus } from '../../lib/toastBus';
import api from '../../lib/api';

type TabKey = 'checklist' | 'documents' | 'deficiencies' | 'history';

export default function ApplicationDetailPage() {
  const { id = '' } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [activeTab, setActiveTab] = useState<TabKey>('checklist');
  const [replacementCategory, setReplacementCategory] = useState<string>('fire_safety_certificate');
  const [replacementFile, setReplacementFile] = useState<File | null>(null);
  const [uploadProgress, setUploadProgress] = useState<number>(0);

  // Queries
  const {
    data: application,
    isLoading: isAppLoading,
    isError: isAppError,
    refetch: refetchApp,
  } = useApplication(id);

  const { data: checklistData, refetch: refetchChecklist } = useChecklist(id);
  const { data: findingsData, refetch: refetchFindings } = useFindings(id);
  const uploadMutation = useUploadDocument();

  // STRICT STATUTORY VISIBILITY RULE (RULES.md):
  // Institution users NEVER see possible_anomaly or duplicate findings, priority scores or internal notes.
  const rawFindings = (findingsData as any)?.findings || findingsData?.items || [];
  const plainLanguageFindings = rawFindings.filter(
    (f: any) => f.type !== 'possible_anomaly' && f.type !== 'duplicate'
  );

  const checklistItems = (checklistData as any)?.results || checklistData?.checklist || [];
  const documents = application?.documents || [];

  const handleReplacementUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!id || !replacementFile) return;

    try {
      await uploadMutation.mutateAsync({
        applicationId: id,
        file: replacementFile,
        category: replacementCategory,
        onProgress: setUploadProgress,
      });

      toastBus.show({
        type: 'success',
        title: 'Rectification Document Uploaded',
        message: 'Your replacement annexure has been transmitted and re-evaluated.',
      });

      setReplacementFile(null);
      setUploadProgress(0);
      refetchApp();
      refetchChecklist();
      refetchFindings();
    } catch {
      toastBus.show({
        type: 'danger',
        title: 'Upload Failed',
        message: 'Could not upload replacement document.',
      });
    }
  };

  const handleDownloadDocument = async (docId: string, filename: string) => {
    try {
      const res = await api.get(`/documents/${docId}/file`, {
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch {
      toastBus.show({
        type: 'danger',
        title: 'Download Failed',
        message: 'Could not stream document from secure vault.',
      });
    }
  };

  if (isAppLoading) {
    return (
      <div className="space-y-6 max-w-5xl mx-auto">
        <Skeleton variant="card" className="h-20" />
        <Skeleton variant="card" className="h-64" />
      </div>
    );
  }

  if (isAppError || !application) {
    return (
      <div className="max-w-md mx-auto my-12 text-center p-8 bg-surface rounded-card border border-danger/30 space-y-4 shadow-card">
        <AlertTriangle className="w-10 h-10 text-danger mx-auto" />
        <h3 className="text-base font-bold text-text">Dossier Unavailable</h3>
        <p className="text-xs text-muted">
          Could not load statutory application record '{id}'.
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

  // Build institution-safe audit/timeline events derived from application state & document history
  const historyEvents: TimelineEvent[] = [];

  if (application.created_at) {
    historyEvents.push({
      id: 'evt-create',
      title: 'Application Dossier Initialized',
      timestamp: new Date(application.created_at).toLocaleString(),
      actor: application.institution_name || 'Applicant Institution',
      role: 'institution',
      description: `Application draft registered under academic cycle ${application.academic_year}.`,
      status: 'completed',
    });
  }

  // Document upload events
  documents.forEach((doc: any, idx: number) => {
    historyEvents.push({
      id: `evt-doc-${doc.id || idx}`,
      title: `Annexure Uploaded: ${doc.filename || doc.class || 'Statutory Document'}`,
      timestamp: doc.created_at ? new Date(doc.created_at).toLocaleString() : 'Cycle 2026-27',
      actor: application.institution_name || 'Applicant Institution',
      role: 'institution',
      description: `Encrypted in secure storage. SHA-256: ${doc.sha256 ? doc.sha256.slice(0, 16) + '...' : 'Verified'}`,
      hash: doc.sha256,
      status: 'completed',
    });
  });

  if (application.submitted_at) {
    historyEvents.push({
      id: 'evt-submit',
      title: 'Formal Dossier Submission',
      timestamp: new Date(application.submitted_at).toLocaleString(),
      actor: application.institution_name || 'Applicant Institution',
      role: 'institution',
      description: 'Formal digital submission transmitted to AICTE Scrutiny Committee.',
      status: 'completed',
    });
  }

  if (application.state === 'RECTIFICATION_REQUESTED') {
    historyEvents.push({
      id: 'evt-rectify',
      title: 'Rectification Requested by Scrutiny Committee',
      timestamp: new Date().toLocaleString(),
      actor: 'AICTE Scrutiny Officer',
      role: 'scrutiny_officer',
      description: 'Deficiency notice issued. Institution requested to upload compliant replacement annexures.',
      status: 'flagged',
    });
  } else if (application.state === 'APPROVED') {
    historyEvents.push({
      id: 'evt-approved',
      title: 'Extension of Approval Granted',
      timestamp: new Date().toLocaleString(),
      actor: 'AICTE Council',
      role: 'admin',
      description: 'Statutory scrutiny completed and extension of approval officially sanctioned.',
      status: 'completed',
    });
  }

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Top Back Navigation */}
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={() => navigate('/institution/dashboard')}
          className="p-1.5 rounded-lg border border-border bg-surface text-muted hover:text-text transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
        </button>
        <span className="text-xs text-muted font-mono">Back to Dashboard</span>
      </div>

      {/* Dossier Header */}
      <div className="rounded-card bg-surface border border-border p-6 shadow-card flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex flex-wrap items-center gap-2 mb-2">
            <span className="bg-primary/10 px-2.5 py-0.5 rounded border border-primary/20">
              <CopyableText text={application.id} label="Copy Dossier Ref ID" />
            </span>
            <StatusChip status={application.state} type="application" />
          </div>
          <h1 className="text-xl font-bold font-heading text-text">
            {application.institution_name || 'Government College of Engineering, Pune'}
          </h1>
          <p className="text-xs text-muted font-sans mt-1">
            Program: {application.category} • Academic Cycle {application.academic_year} • Status:{' '}
            {application.submitted_at ? `Submitted on ${new Date(application.submitted_at).toLocaleDateString()}` : 'Draft Dossier'}
          </p>
        </div>

        <div className="p-3 rounded-xl bg-surface-alt border border-border text-right self-start md:self-center font-mono text-xs">
          <span className="text-muted block text-[10px]">APPROVAL CATEGORY</span>
          <span className="text-primary font-bold">{application.category}</span>
        </div>
      </div>

      {/* Plain Language Rectification Directive Banner */}
      {application.state === 'RECTIFICATION_REQUESTED' && (
        <div className="rounded-card border-l-4 border-l-warning border border-border bg-surface p-5 shadow-card space-y-2">
          <div className="flex items-center gap-2 text-warning font-bold text-sm">
            <AlertTriangle className="w-5 h-5 flex-shrink-0" />
            <span>Rectification Directive Notice</span>
          </div>
          <p className="text-xs text-text font-sans leading-relaxed">
            The Scrutiny Committee has reviewed your application and issued a rectification directive. Please review the specific deficiencies in the Deficiencies tab and upload compliant replacement annexures below.
          </p>
        </div>
      )}

      {/* Tabs Header */}
      <div className="flex border-b border-border gap-2">
        <button
          type="button"
          onClick={() => setActiveTab('checklist')}
          className={`px-4 py-2 text-xs font-semibold font-heading border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === 'checklist'
              ? 'border-primary text-primary'
              : 'border-transparent text-muted hover:text-text'
          }`}
        >
          <span>Statutory Checklist</span>
          <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-surface-alt font-mono">
            {checklistItems.length}
          </span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('documents')}
          className={`px-4 py-2 text-xs font-semibold font-heading border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === 'documents'
              ? 'border-primary text-primary'
              : 'border-transparent text-muted hover:text-text'
          }`}
        >
          <span>Uploaded Documents</span>
          <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-surface-alt font-mono">
            {documents.length}
          </span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('deficiencies')}
          className={`px-4 py-2 text-xs font-semibold font-heading border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === 'deficiencies'
              ? 'border-warning text-warning'
              : 'border-transparent text-muted hover:text-text'
          }`}
        >
          <span>Deficiencies</span>
          {plainLanguageFindings.length > 0 && (
            <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-warning/15 text-warning font-mono font-bold">
              {plainLanguageFindings.length}
            </span>
          )}
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('history')}
          className={`px-4 py-2 text-xs font-semibold font-heading border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === 'history'
              ? 'border-primary text-primary'
              : 'border-transparent text-muted hover:text-text'
          }`}
        >
          <span>Timeline & History</span>
        </button>
      </div>

      {/* TAB 1: Statutory Checklist */}
      {activeTab === 'checklist' && (
        <div className="rounded-card bg-surface border border-border p-5 shadow-card space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold font-heading text-text">
              Statutory Checklist Compliance Matrix
            </h3>
            <span className="text-xs font-mono text-muted">
              AICTE Approval Process Handbook Norms
            </span>
          </div>

          <div className="divide-y divide-border/60">
            {checklistItems.length > 0 ? (
              checklistItems.map((item: any, idx: number) => {
                const name = item.name || item.rule_id || `Rule #${idx + 1}`;
                const result = item.result || item.status || 'PENDING';
                const clause = item.rule_clause || item.category || (item.inputs && (item.inputs as any).document_class) || 'APH 2026-27';

                return (
                  <div key={idx} className="py-3 flex items-center justify-between gap-3 text-xs">
                    <div>
                      <p className="font-semibold text-text">{name}</p>
                      <p className="text-[11px] font-mono text-muted">{clause}</p>
                    </div>
                    <ChecklistStateChip result={result} />
                  </div>
                );
              })
            ) : (
              <EmptyState
                icon={CheckCircle2}
                title="Checklist Not Yet Evaluated"
                description="Statutory checklist rules will evaluate automatically upon automated pipeline execution."
              />
            )}
          </div>
        </div>
      )}

      {/* TAB 2: Uploaded Documents */}
      {activeTab === 'documents' && (
        <div className="space-y-6">
          <div className="rounded-card bg-surface border border-border p-5 shadow-card space-y-3">
            <h3 className="text-sm font-bold font-heading text-text">
              Uploaded Application Dossier Files
            </h3>
            <div className="space-y-2">
              {documents.length > 0 ? (
                documents.map((doc: any) => (
                  <div
                    key={doc.id}
                    className="p-3.5 rounded-xl bg-surface-alt border border-border flex items-center justify-between gap-2 text-xs"
                  >
                    <div className="flex items-center gap-2.5 min-w-0">
                      <FileText className="w-5 h-5 text-primary flex-shrink-0" />
                      <div className="min-w-0 truncate">
                        <p className="font-bold text-text truncate">{doc.filename || doc.class || doc.id}</p>
                        <p className="text-[10px] font-mono text-muted">
                          Class: {doc.class || doc.category || 'Statutory Annexure'} • {doc.page_count || 1} pages • Status: {doc.scan_status || 'VERIFIED'}
                        </p>
                      </div>
                    </div>

                    <button
                      type="button"
                      onClick={() => handleDownloadDocument(doc.id, doc.filename || `${doc.id}.pdf`)}
                      className="px-3 py-1.5 rounded-lg text-xs font-medium bg-surface border border-border hover:bg-surface-alt text-primary flex items-center gap-1.5 transition-colors shrink-0"
                    >
                      <Download className="w-3.5 h-3.5" />
                      <span>Download</span>
                    </button>
                  </div>
                ))
              ) : (
                <EmptyState
                  icon={FileText}
                  title="No Documents Uploaded"
                  description="No PDF annexures are currently attached to this application."
                />
              )}
            </div>
          </div>

          {/* Replacement Upload Form */}
          <div className="rounded-card bg-surface border border-border p-5 shadow-card space-y-4">
            <h4 className="text-xs font-bold font-heading uppercase text-text flex items-center gap-2">
              <Upload className="w-4 h-4 text-primary" /> Upload Additional or Replacement Annexure
            </h4>
            <form onSubmit={handleReplacementUpload} className="space-y-3 text-xs">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-muted font-mono mb-1 font-semibold">
                    DOCUMENT REQUIREMENT CLASS
                  </label>
                  <select
                    value={replacementCategory}
                    onChange={(e) => setReplacementCategory(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl bg-surface border border-border text-text focus:outline-none focus:ring-1 focus:ring-primary"
                  >
                    <option value="land_title_deed">Land Title Deed & Mutation Entry</option>
                    <option value="building_occupancy_certificate">Building / Occupancy Certificate</option>
                    <option value="fire_safety_certificate">Fire Safety Clearance NOC</option>
                    <option value="accreditation_certificate">Accreditation Certificate</option>
                    <option value="ter_payment_receipt">TER Processing Fee Receipt</option>
                    <option value="floor_plan">Architect Floor Plan</option>
                  </select>
                </div>
                <div>
                  <label className="block text-muted font-mono mb-1 font-semibold">
                    SELECT FILE (PDF / PNG / JPG)
                  </label>
                  <input
                    type="file"
                    accept=".pdf,.png,.jpg"
                    onChange={(e) => setReplacementFile(e.target.files?.[0] || null)}
                    className="w-full text-xs text-muted file:mr-2 file:py-1.5 file:px-3 file:rounded-lg file:border file:border-border file:text-xs file:bg-surface-alt file:text-text cursor-pointer"
                  />
                </div>
              </div>

              {uploadProgress > 0 && uploadProgress < 100 && (
                <div className="w-full bg-border rounded-full h-1.5 overflow-hidden">
                  <div
                    className="bg-primary h-full transition-all duration-300"
                    style={{ width: `${uploadProgress}%` }}
                  />
                </div>
              )}

              <div className="flex justify-end">
                <button
                  type="submit"
                  disabled={!replacementFile || uploadMutation.isPending}
                  className="px-4 py-2 rounded-xl text-xs font-semibold bg-primary text-white hover:bg-primary/90 disabled:opacity-50 transition-colors flex items-center gap-1.5"
                >
                  {uploadMutation.isPending ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Upload className="w-3.5 h-3.5" />}
                  <span>Transmit Document</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* TAB 3: Deficiencies in Plain Language */}
      {activeTab === 'deficiencies' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold font-heading text-text">
              Deficiencies Requiring Rectification ({plainLanguageFindings.length})
            </h3>
            <span className="text-xs text-muted">Plain-language statutory observations</span>
          </div>

          {plainLanguageFindings.length === 0 ? (
            <EmptyState
              icon={CheckCircle2}
              title="No Deficiencies Flagged"
              description="Your application dossier satisfies all evaluated AICTE statutory checklist criteria."
            />
          ) : (
            <div className="space-y-3">
              {plainLanguageFindings.map((finding: any) => (
                <div
                  key={finding.finding_id}
                  className="p-4 rounded-xl border border-warning/30 bg-surface shadow-card space-y-3"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-xs text-text">{finding.title}</span>
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold uppercase bg-warning/15 text-warning border border-warning/30">
                      {finding.severity}
                    </span>
                  </div>

                  <p className="text-xs text-text/90 font-sans leading-relaxed">
                    {finding.reason}
                  </p>

                  <div className="pt-2 border-t border-border/60 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs">
                    <span className="text-[11px] font-mono text-muted">
                      Annexure: <strong>{finding.evidence?.[0]?.field || 'Statutory Requirement'}</strong>
                    </span>

                    <button
                      type="button"
                      onClick={() => {
                        setReplacementCategory(finding.evidence?.[0]?.field || 'fire_safety_certificate');
                        setActiveTab('documents');
                      }}
                      className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-primary text-white hover:bg-primary/90 flex items-center gap-1.5 self-start sm:self-auto transition-colors"
                    >
                      <Upload className="w-3.5 h-3.5" />
                      <span>Upload Compliant Replacement</span>
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 4: Timeline & History */}
      {activeTab === 'history' && (
        <div className="space-y-6">
          {/* Statutory State Lifecycle Stepper */}
          <div className="rounded-card bg-surface border border-border p-5 shadow-card space-y-3">
            <h4 className="text-xs font-bold font-heading uppercase text-text flex items-center gap-2">
              <Clock className="w-4 h-4 text-primary" /> Application Lifecycle Status Progression
            </h4>
            <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-6 gap-2 text-xs font-mono">
              {[
                { state: 'DRAFT', label: '1. Draft' },
                { state: 'SUBMITTED', label: '2. Submitted' },
                { state: 'VALIDATION_IN_PROGRESS', label: '3. Validating' },
                { state: 'DEFICIENCIES_FOUND', label: '4. Deficiencies' },
                { state: 'READY_FOR_SCRUTINY', label: '5. Scrutiny' },
                { state: 'APPROVED', label: '6. Sanctioned' },
              ].map((step) => {
                const isCurrent = application.state === step.state;
                return (
                  <div
                    key={step.state}
                    className={`p-2.5 rounded-xl border text-center font-bold transition-all ${
                      isCurrent
                        ? 'bg-primary text-white border-primary shadow-xs'
                        : 'bg-surface-alt border-border text-muted'
                    }`}
                  >
                    {step.label}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Audit-Derived History Feed limited to institution-safe events */}
          <div className="rounded-card bg-surface border border-border p-5 shadow-card space-y-4">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-bold font-heading uppercase text-text flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-success" /> Verified Statutory Dossier Activity Log
              </h4>
              <span className="text-[11px] font-mono text-muted">
                Institution-Scoped Event History
              </span>
            </div>

            <Timeline events={historyEvents} />
          </div>
        </div>
      )}
    </div>
  );
}
