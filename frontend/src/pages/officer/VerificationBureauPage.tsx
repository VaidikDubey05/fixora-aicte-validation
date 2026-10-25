import { useState } from 'react';
import {
  Database,
  CheckCircle2,
  AlertTriangle,
  RotateCcw,
  RefreshCw,
  ShieldCheck,
  FileCheck2,
} from 'lucide-react';
import { KpiCard } from '../../components/KpiCard';
import { DataTable, Column } from '../../components/DataTable';
import { StatusChip } from '../../components/StatusChip';
import { SimulatedBadge } from '../../components/SimulatedBadge';
import { AdvisoryBanner } from '../../components/AdvisoryBanner';
import { Skeleton } from '../../components/Skeleton';
import { EmptyState } from '../../components/EmptyState';
import { Modal } from '../../components/Modal';
import {
  useVerificationQueue,
  useVerifyDocument,
  useManualConfirm,
  VerificationQueueItem,
} from '../../api';

export default function VerificationBureauPage() {
  const { data, isLoading, isError, refetch } = useVerificationQueue();
  const verifyDoc = useVerifyDocument();
  const manualConfirm = useManualConfirm();

  const [selectedRecord, setSelectedRecord] = useState<VerificationQueueItem | null>(null);
  const [overrideModalOpen, setOverrideModalOpen] = useState(false);
  const [overrideNotes, setOverrideNotes] = useState('');
  const [overrideOutcome, setOverrideOutcome] = useState('VERIFIED');
  const [evidenceFile, setEvidenceFile] = useState<File | null>(null);
  const [actionRecord, setActionRecord] = useState<VerificationQueueItem | null>(null);

  const items = data?.items || [];

  // Derived KPIs
  const totalItems = data?.total ?? items.length;
  const verifiedCount = items.filter((i) => i.status === 'VERIFIED').length;
  const mismatchCount = items.filter(
    (i) => i.status === 'MISMATCH_DETECTED' || i.status === 'EXPIRED'
  ).length;
  const outageCount = items.filter(
    (i) => i.status === 'SOURCE_UNAVAILABLE' || i.status === 'VERIFICATION_PENDING'
  ).length;

  const handleRetry = async (docId: string) => {
    try {
      await verifyDoc.mutateAsync(docId);
    } catch {
      // Error handled by api toast
    }
  };

  const handleOpenOverride = (record: VerificationQueueItem) => {
    setActionRecord(record);
    setOverrideOutcome(record.status === 'MISMATCH_DETECTED' ? 'VERIFIED' : 'VERIFIED');
    setOverrideNotes('');
    setEvidenceFile(null);
    setOverrideModalOpen(true);
  };

  const handleManualOverrideSubmit = async () => {
    if (!actionRecord || !overrideNotes.trim()) return;
    try {
      await manualConfirm.mutateAsync({
        verificationId: actionRecord.document_id || String(actionRecord.record_id),
        outcome: overrideOutcome,
        notes: overrideNotes.trim(),
      });
      setOverrideModalOpen(false);
      setActionRecord(null);
      setOverrideNotes('');
      setEvidenceFile(null);
    } catch {
      // Handled by api toast
    }
  };

  const columns: Column<VerificationQueueItem>[] = [
    {
      key: 'record_id',
      header: 'Queue Item',
      sortable: true,
      accessor: (row) => (
        <div>
          <span className="font-mono font-bold text-primary block">
            VER-DOC-{row.document_id?.slice(0, 8) || row.record_id}
          </span>
          <span className="text-[11px] font-mono text-muted">Doc ID: {row.document_id}</span>
        </div>
      ),
    },
    {
      key: 'application_id',
      header: 'Application & Class',
      sortable: true,
      accessor: (row) => (
        <div>
          <p className="font-semibold text-text text-xs uppercase">{row.class_name?.replace(/_/g, ' ') || 'Statutory Annexure'}</p>
          <span className="text-[11px] font-mono text-muted">{row.application_id}</span>
        </div>
      ),
    },
    {
      key: 'source_name',
      header: 'Statutory Registry Source',
      accessor: (row) => (
        <div className="flex items-center gap-1.5 flex-wrap">
          <SimulatedBadge sourceName={row.source_name || 'External Statutory Gateway'} />
        </div>
      ),
    },
    {
      key: 'status',
      header: 'Registry Status',
      sortable: true,
      accessor: (row) => <StatusChip status={row.status} type="verification" />,
    },
    {
      key: 'timestamp',
      header: 'Last Checked',
      sortable: true,
      accessor: (row) => (
        <span className="text-xs text-muted">
          {row.timestamp ? new Date(row.timestamp).toLocaleString() : 'Recent'}
        </span>
      ),
    },
    {
      key: 'actions',
      header: 'Actions',
      className: 'text-right',
      accessor: (row) => (
        <div className="flex items-center justify-end gap-2">
          <button
            type="button"
            onClick={() => setSelectedRecord(row)}
            className="px-2.5 py-1 rounded-md text-xs font-semibold bg-surface-alt hover:bg-border text-text border border-border transition-colors"
          >
            Details
          </button>
          <button
            type="button"
            onClick={() => handleRetry(row.document_id)}
            disabled={verifyDoc.isPending}
            className="p-1 rounded-md text-muted hover:text-primary hover:bg-surface-alt border border-transparent hover:border-border transition-colors disabled:opacity-50"
            title="Retry Statutory Verification"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${verifyDoc.isPending ? 'animate-spin' : ''}`} />
          </button>
          <button
            type="button"
            onClick={() => handleOpenOverride(row)}
            className="px-2.5 py-1 rounded-md text-xs font-semibold bg-primary/10 hover:bg-primary/20 text-primary transition-colors flex items-center gap-1"
          >
            <ShieldCheck className="w-3.5 h-3.5" />
            Override
          </button>
        </div>
      ),
    },
  ];

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton variant="card" className="h-20" />
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <Skeleton key={i} variant="card" className="h-24" />
          ))}
        </div>
        <Skeleton variant="card" className="h-96" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="p-8 rounded-card bg-surface border border-danger/30 text-center space-y-4">
        <div className="w-12 h-12 rounded-full bg-danger/10 text-danger flex items-center justify-center mx-auto">
          <AlertTriangle className="w-6 h-6" />
        </div>
        <h2 className="text-base font-bold text-text">Failed to load verification queue</h2>
        <p className="text-xs text-muted max-w-md mx-auto">
          Could not communicate with the verification bureau services.
        </p>
        <button
          type="button"
          onClick={() => refetch()}
          className="px-4 py-2 bg-primary text-white text-xs font-semibold rounded-lg hover:bg-primary/90"
        >
          Retry Connection
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold font-heading text-text">
            Verification Bureau Gateway
          </h1>
          <p className="text-xs text-muted font-sans mt-0.5">
            Automated Cross-Referencing against Statutory State & Central Registries
          </p>
        </div>
        <button
          type="button"
          onClick={() => refetch()}
          className="inline-flex items-center gap-2 px-3 py-1.5 text-xs font-semibold rounded-lg bg-surface border border-border hover:bg-surface-alt text-text transition-colors self-start sm:self-auto"
        >
          <RotateCcw className="w-3.5 h-3.5 text-muted" />
          Refresh Queue
        </button>
      </div>

      {/* Advisory Banner */}
      <AdvisoryBanner
        confidence={98.2}
        sourceName="Statutory Bureau Gateway Integrations"
        message="A source outage is never an adverse conclusion. If an external registry is unreachable, manual review is queued without penalising the applicant."
      />

      {/* KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <KpiCard
          title="Queue Items"
          value={totalItems}
          subtitle="Awaiting Bureau Verification"
          icon={Database}
          badge={{ text: 'Active', variant: 'primary' }}
        />
        <KpiCard
          title="Verified Matches"
          value={verifiedCount}
          subtitle="Conclusive match"
          icon={CheckCircle2}
          badge={{ text: 'Verified', variant: 'success' }}
        />
        <KpiCard
          title="Mismatches Detected"
          value={mismatchCount}
          subtitle="Discrepancy queue"
          icon={AlertTriangle}
          badge={{ text: 'Action Needed', variant: 'warning' }}
        />
        <KpiCard
          title="Gateway Outages / Pending"
          value={outageCount}
          subtitle="Non-adverse state"
          icon={RotateCcw}
          badge={{ text: 'Neutral', variant: 'secondary' }}
        />
      </div>

      {/* Side-by-side comparison pane if selected */}
      {selectedRecord && (
        <div className="rounded-card bg-surface border border-primary/30 p-5 shadow-card space-y-4">
          <div className="flex items-center justify-between border-b border-border pb-3">
            <div>
              <span className="font-mono text-xs text-primary font-bold">
                Item: {selectedRecord.document_id}
              </span>
              <h3 className="text-sm font-bold font-heading text-text">
                Statutory Cross-Verification: {selectedRecord.class_name?.replace(/_/g, ' ') || 'Annexure'}
              </h3>
            </div>
            <div className="flex items-center gap-2">
              <StatusChip status={selectedRecord.status} type="verification" />
              <button
                type="button"
                onClick={() => setSelectedRecord(null)}
                className="text-muted hover:text-text text-xs p-1"
              >
                ✕ Close
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Declared Claim */}
            <div className="p-4 rounded-xl bg-surface-alt border border-border space-y-2">
              <span className="text-[10px] font-mono text-muted uppercase font-bold block">
                Applicant Application Reference
              </span>
              <p className="text-sm font-mono font-bold text-text">
                {selectedRecord.application_id}
              </p>
              <div className="text-xs text-muted pt-2 border-t border-border">
                <span className="font-semibold text-text block mb-1">Message / Claim Note:</span>
                <p className="font-mono text-[11px] bg-surface p-2 rounded border border-border">
                  {selectedRecord.message || 'No additional claimant commentary attached.'}
                </p>
              </div>
            </div>

            {/* Registry Record */}
            <div className="p-4 rounded-xl bg-surface-alt border border-secondary/30 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-mono text-secondary uppercase font-bold block">
                  Statutory Registry Feed
                </span>
                <SimulatedBadge sourceName={selectedRecord.source_name || 'External Statutory Service'} />
              </div>
              <p className="text-sm font-bold font-heading text-text">
                Status: <span className="font-mono">{selectedRecord.status}</span>
              </p>
              <div className="text-xs text-muted pt-2 border-t border-border">
                <span className="font-semibold text-text block mb-1">Mismatch Details / Telemetry:</span>
                {selectedRecord.mismatch_details ? (
                  <pre className="font-mono text-[11px] bg-surface p-2 rounded border border-border overflow-x-auto">
                    {JSON.stringify(selectedRecord.mismatch_details, null, 2)}
                  </pre>
                ) : (
                  <p className="text-xs text-muted italic">No discrepancy logged by external gateway.</p>
                )}
              </div>
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2 border-t border-border">
            <button
              type="button"
              onClick={() => handleRetry(selectedRecord.document_id)}
              disabled={verifyDoc.isPending}
              className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-surface border border-border hover:bg-surface-alt text-text flex items-center gap-1.5"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${verifyDoc.isPending ? 'animate-spin' : ''}`} />
              Re-query Registry
            </button>
            <button
              type="button"
              onClick={() => handleOpenOverride(selectedRecord)}
              className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-primary text-white hover:bg-primary/90 flex items-center gap-1.5"
            >
              <ShieldCheck className="w-3.5 h-3.5" />
              Manual Confirmation
            </button>
          </div>
        </div>
      )}

      {/* Verification Records Table */}
      <div className="space-y-3">
        <h2 className="text-sm font-bold font-heading text-text">
          Statutory Verification Bureau Queue
        </h2>
        {items.length === 0 ? (
          <EmptyState
            icon={FileCheck2}
            title="Verification queue is clear"
            description="All statutory registry checks have completed or there are no documents requiring officer attention."
          />
        ) : (
          <DataTable
            data={items}
            columns={columns}
            searchPlaceholder="Search verification logs..."
          />
        )}
      </div>

      {/* Manual Override Confirmation Modal */}
      <Modal
        isOpen={overrideModalOpen}
        onClose={() => setOverrideModalOpen(false)}
        title="Officer Manual Verification Override"
        footer={
          <div className="flex items-center justify-end gap-2 w-full">
            <button
              type="button"
              onClick={() => setOverrideModalOpen(false)}
              className="px-3 py-1.5 rounded-lg text-xs font-medium bg-surface-alt hover:bg-border text-text transition-colors"
            >
              Cancel
            </button>
            <button
              type="button"
              disabled={!overrideNotes.trim() || manualConfirm.isPending}
              onClick={handleManualOverrideSubmit}
              className="px-4 py-1.5 rounded-lg text-xs font-semibold bg-primary text-white hover:bg-primary/90 disabled:opacity-50 transition-colors flex items-center gap-1.5"
            >
              <ShieldCheck className="w-3.5 h-3.5" />
              Confirm Override Decision
            </button>
          </div>
        }
      >
        <div className="space-y-4">
          <p className="text-xs text-muted">
            As an authorised verification officer, you may manually verify or override the external registry check. An immutable audit record will be logged with your digital identity.
          </p>

          <div>
            <label className="block text-xs font-semibold text-text mb-1">
              Determination Outcome
            </label>
            <select
              value={overrideOutcome}
              onChange={(e) => setOverrideOutcome(e.target.value)}
              className="w-full text-xs rounded-lg border border-border bg-surface px-3 py-2 text-text focus:outline-none focus:ring-1 focus:ring-primary"
            >
              <option value="VERIFIED">VERIFIED - Authenticity Confirmed Manually</option>
              <option value="MISMATCH_DETECTED">MISMATCH_DETECTED - Officer Found Discrepancy</option>
              <option value="EXPIRED">EXPIRED - Statutory Validity Elapsed</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-text mb-1">
              Mandatory Determination Notes & Justification <span className="text-danger">*</span>
            </label>
            <textarea
              rows={3}
              value={overrideNotes}
              onChange={(e) => setOverrideNotes(e.target.value)}
              placeholder="Provide statutory reference, manual cross-check details, or physical verification record..."
              className="w-full text-xs rounded-lg border border-border bg-surface px-3 py-2 text-text placeholder:text-muted focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-text mb-1">
              Affidavit / Registry Evidence Attachment (Optional)
            </label>
            <input
              type="file"
              accept=".pdf,.png,.jpg"
              onChange={(e) => setEvidenceFile(e.target.files?.[0] || null)}
              className="w-full text-xs text-muted file:mr-2 file:py-1 file:px-2.5 file:rounded-lg file:border file:border-border file:text-xs file:bg-surface-alt file:text-text cursor-pointer"
            />
            {evidenceFile && (
              <span className="text-[11px] font-mono text-primary mt-1 block">
                Evidence: {evidenceFile.name} ({(evidenceFile.size / 1024).toFixed(1)} KB)
              </span>
            )}
          </div>
        </div>
      </Modal>
    </div>
  );
}