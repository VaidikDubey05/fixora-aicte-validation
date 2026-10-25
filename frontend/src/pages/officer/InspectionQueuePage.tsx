import { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Building2,
  CheckCircle2,
  AlertTriangle,
  RotateCcw,
  ExternalLink,
  ClipboardList,
} from 'lucide-react';
import { KpiCard } from '../../components/KpiCard';
import { DataTable, Column } from '../../components/DataTable';
import { AdvisoryBanner } from '../../components/AdvisoryBanner';
import { StatusChip } from '../../components/StatusChip';
import { SeverityChip } from '../../components/SeverityChip';
import { Skeleton } from '../../components/Skeleton';
import { EmptyState } from '../../components/EmptyState';
import { Modal } from '../../components/Modal';
import { useInspectionQueue } from '../../api';

interface InspectionItem {
  application_id: string;
  institution_id: string;
  state: string;
  priority_score: number;
  referred_findings: Array<{
    finding_id: string;
    title: string;
    reason: string;
    severity: string;
    status: string;
  }>;
  created_at: string;
}

export default function InspectionQueuePage() {
  const { data, isLoading, isError, refetch } = useInspectionQueue();
  const [selectedItem, setSelectedItem] = useState<InspectionItem | null>(null);

  const rawItems = (data?.items || []) as unknown as InspectionItem[];

  const totalReferrals = rawItems.length;
  const highPriority = rawItems.filter((i) => (i.priority_score || 0) >= 70).length;
  const pendingVisits = rawItems.filter((i) => i.state === 'REFERRED_FOR_INSPECTION').length;

  const columns: Column<InspectionItem>[] = [
    {
      key: 'application_id',
      header: 'Application Ref ID',
      sortable: true,
      accessor: (row) => (
        <div>
          <span className="font-mono font-bold text-primary block">{row.application_id}</span>
          <span className="text-[11px] font-mono text-muted">Inst: {row.institution_id}</span>
        </div>
      ),
    },
    {
      key: 'state',
      header: 'Dossier State',
      sortable: true,
      accessor: (row) => <StatusChip status={row.state} type="application" />,
    },
    {
      key: 'priority_score',
      header: 'Priority Index',
      sortable: true,
      accessor: (row) => (
        <span
          className={`font-mono text-xs font-bold px-2 py-0.5 rounded ${
            row.priority_score >= 70
              ? 'bg-danger/10 text-danger'
              : row.priority_score >= 40
              ? 'bg-warning/10 text-warning'
              : 'bg-success/10 text-success'
          }`}
        >
          {row.priority_score} / 100
        </span>
      ),
    },
    {
      key: 'referred_findings',
      header: 'Inspection Findings',
      accessor: (row) => (
        <div className="flex flex-col gap-1 max-w-md">
          {row.referred_findings.length === 0 ? (
            <span className="text-xs text-muted">Dossier marked for on-site inspection committee</span>
          ) : (
            row.referred_findings.slice(0, 2).map((f) => (
              <div key={f.finding_id} className="text-xs text-text flex items-center gap-1.5">
                <SeverityChip severity={f.severity} />
                <span className="truncate">{f.title}</span>
              </div>
            ))
          )}
          {row.referred_findings.length > 2 && (
            <span className="text-[11px] text-primary font-medium">
              +{row.referred_findings.length - 2} more items
            </span>
          )}
        </div>
      ),
    },
    {
      key: 'created_at',
      header: 'Submitted',
      sortable: true,
      accessor: (row) => (
        <span className="text-xs text-muted">
          {new Date(row.created_at).toLocaleDateString()}
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
            onClick={() => setSelectedItem(row)}
            className="px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-surface-alt hover:bg-border text-text border border-border transition-colors"
          >
            Review Findings
          </button>
          <Link
            to={`/officer/applications/${row.application_id}`}
            className="p-1.5 rounded-lg text-muted hover:text-primary hover:bg-surface-alt border border-transparent hover:border-border transition-colors"
            title="Open Scrutiny Workspace"
          >
            <ExternalLink className="w-4 h-4" />
          </Link>
        </div>
      ),
    },
  ];

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton variant="card" className="h-20" />
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {[...Array(3)].map((_, i) => (
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
        <h2 className="text-base font-bold text-text">Failed to load inspection queue</h2>
        <p className="text-xs text-muted max-w-md mx-auto">
          Could not communicate with the statutory inspection service.
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
      {/* Title */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold font-heading text-text">
            Infrastructure & Spatial Inspection Desk
          </h1>
          <p className="text-xs text-muted font-sans mt-0.5">
            AICTE APH 2026-27 Land Geometry, FAR/FSI, and Expert Inspection Referrals
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
        confidence={94.9}
        sourceName="Survey of India Geospatial Portal"
        message="Infrastructure outputs are strictly diagnostic: 'consistent', 'needs_additional_evidence', or 'recommend_inspection'. The system never issues binary pass/fail verdicts."
      />

      {/* KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <KpiCard
          title="Inspection Referrals"
          value={totalReferrals}
          subtitle="Awaiting Expert Committee"
          icon={Building2}
          badge={{ text: 'Active Queue', variant: 'primary' }}
        />
        <KpiCard
          title="High Priority Cases"
          value={highPriority}
          subtitle="Score >= 70"
          icon={AlertTriangle}
          badge={{ text: 'Expedited Scrutiny', variant: 'danger' }}
        />
        <KpiCard
          title="Referred for Site Visit"
          value={pendingVisits}
          subtitle="State: REFERRED_FOR_INSPECTION"
          icon={CheckCircle2}
          badge={{ text: 'Nominated', variant: 'warning' }}
        />
      </div>

      {/* Inspection Queue Table */}
      <div className="space-y-3">
        <h2 className="text-sm font-bold font-heading text-text">
          Referred Infrastructure Applications
        </h2>
        {rawItems.length === 0 ? (
          <EmptyState
            icon={ClipboardList}
            title="Inspection queue is clear"
            description="No applications are currently flagged for on-site committee inspection."
          />
        ) : (
          <DataTable
            data={rawItems}
            columns={columns}
            searchPlaceholder="Search inspection referrals..."
          />
        )}
      </div>

      {/* Details Modal */}
      {selectedItem && (
        <Modal
          isOpen={!!selectedItem}
          onClose={() => setSelectedItem(null)}
          title={`Inspection Diagnostic: ${selectedItem.application_id}`}
          footer={
            <div className="flex items-center justify-between w-full">
              <span className="font-mono text-xs text-muted">
                Institution ID: {selectedItem.institution_id}
              </span>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setSelectedItem(null)}
                  className="px-3 py-1.5 rounded-lg text-xs font-medium bg-surface-alt hover:bg-border text-text transition-colors"
                >
                  Close
                </button>
                <Link
                  to={`/officer/applications/${selectedItem.application_id}`}
                  className="px-4 py-1.5 rounded-lg text-xs font-semibold bg-primary text-white hover:bg-primary/90 transition-colors inline-flex items-center gap-1.5"
                >
                  Open Scrutiny Workspace
                  <ExternalLink className="w-3.5 h-3.5" />
                </Link>
              </div>
            </div>
          }
        >
          <div className="space-y-4">
            <div className="p-3 bg-surface-alt rounded-lg border border-border flex items-center justify-between">
              <div>
                <span className="text-[10px] font-mono uppercase text-muted font-bold block">
                  Application State
                </span>
                <StatusChip status={selectedItem.state} type="application" />
              </div>
              <div>
                <span className="text-[10px] font-mono uppercase text-muted font-bold block">
                  Priority Score
                </span>
                <span className="font-mono font-bold text-sm text-text">
                  {selectedItem.priority_score} / 100
                </span>
              </div>
            </div>

            <div>
              <h4 className="text-xs font-bold text-text mb-2">
                Referred Findings & Spatial Discrepancies
              </h4>
              {selectedItem.referred_findings.length === 0 ? (
                <p className="text-xs text-muted">
                  The application state was formally set to REFERRED_FOR_INSPECTION by an authorised scrutiny officer.
                </p>
              ) : (
                <div className="space-y-2 max-h-60 overflow-y-auto">
                  {selectedItem.referred_findings.map((f) => (
                    <div
                      key={f.finding_id}
                      className="p-3 rounded-lg border border-border bg-surface-alt space-y-1.5"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-xs font-bold text-text">
                          {f.finding_id}
                        </span>
                        <SeverityChip severity={f.severity} />
                      </div>
                      <p className="text-xs font-semibold text-text">{f.title}</p>
                      <p className="text-xs text-muted font-sans">{f.reason}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}
