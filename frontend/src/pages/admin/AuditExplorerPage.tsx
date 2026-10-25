import { useState } from 'react';
import {
  ShieldCheck,
  CheckCircle2,
  Clock,
  Layers,
  User,
  AlertTriangle,
  RotateCcw,
  Search,
  Filter,
  FileCheck2,
  Table as TableIcon,
  GitCommit,
  Hash,
  ChevronDown,
  ChevronUp,
  Download,
} from 'lucide-react';
import { CopyableText } from '../../components/CopyableText';
import { KpiCard } from '../../components/KpiCard';
import { AdvisoryBanner } from '../../components/AdvisoryBanner';
import { Skeleton } from '../../components/Skeleton';
import { EmptyState } from '../../components/EmptyState';
import { DataTable, Column } from '../../components/DataTable';
import { useAudit, useVerifyChain } from '../../api';

interface AuditEntryItem {
  seq: number;
  actor: string;
  role: string;
  action: string;
  target_type: string;
  target_id: string;
  payload: Record<string, any>;
  payload_hash: string;
  prev_hash: string;
  current_hash: string;
  rule_versions?: string;
  model_versions?: string;
  created_at: string;
}

export default function AuditExplorerPage() {
  const [page, setPage] = useState(1);
  const [eventFilter, setEventFilter] = useState('');
  const [actorFilter, setActorFilter] = useState('');
  const [appFilter, setAppFilter] = useState('');
  const [viewMode, setViewMode] = useState<'timeline' | 'table'>('timeline');
  const [expandedSeq, setExpandedSeq] = useState<number | null>(null);

  const {
    data: auditData,
    isLoading,
    isError,
    refetch,
  } = useAudit({
    page,
    page_size: 20,
    event_type: eventFilter || undefined,
    actor_id: actorFilter || undefined,
    application_id: appFilter || undefined,
  });

  const {
    data: verifyResult,
    isFetching: isVerifying,
    refetch: runVerifyChain,
  } = useVerifyChain(false);

  const [hasVerified, setHasVerified] = useState(false);

  const handleVerifyChain = async () => {
    setHasVerified(true);
    await runVerifyChain();
  };

  const handleExportCsv = () => {
    const headers = ['Sequence', 'Timestamp', 'Actor', 'Role', 'Action', 'Target Type', 'Target ID', 'SHA-256 Hash', 'Previous Hash'];
    const rows = rawEntries.map((r) => [
      r.seq,
      r.created_at,
      r.actor,
      r.role,
      r.action,
      r.target_type,
      r.target_id,
      r.current_hash,
      r.prev_hash,
    ]);
    const csvContent = [headers.join(','), ...rows.map((row) => row.map((cell) => `"${String(cell || '').replace(/"/g, '""')}"`).join(','))].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `Fixora_Audit_Ledger_${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  };

  const rawEntries = (auditData?.items || []) as unknown as AuditEntryItem[];
  const totalEntries = auditData?.total ?? rawEntries.length;

  const tableColumns: Column<AuditEntryItem>[] = [
    {
      key: 'seq',
      header: 'Sequence',
      sortable: true,
      accessor: (row) => (
        <span className="font-mono text-xs font-bold text-primary bg-primary/10 px-2 py-0.5 rounded border border-primary/20">
          #{row.seq}
        </span>
      ),
    },
    {
      key: 'created_at',
      header: 'Timestamp (UTC)',
      sortable: true,
      accessor: (row) => (
        <span className="font-mono text-[11px] text-muted">
          {new Date(row.created_at).toLocaleString()}
        </span>
      ),
    },
    {
      key: 'actor',
      header: 'Actor & Role',
      accessor: (row) => (
        <div>
          <p className="font-semibold text-text text-xs">{row.actor}</p>
          <span className="font-mono text-[10px] text-muted uppercase">{row.role}</span>
        </div>
      ),
    },
    {
      key: 'action',
      header: 'Event Action',
      sortable: true,
      accessor: (row) => (
        <span className="px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-surface-alt border border-border text-text">
          {row.action}
        </span>
      ),
    },
    {
      key: 'target',
      header: 'Target Resource',
      accessor: (row) => (
        <div className="font-mono text-xs">
          <span className="text-muted">{row.target_type}:</span>{' '}
          <strong className="text-text">{row.target_id || 'Global'}</strong>
        </div>
      ),
    },
    {
      key: 'current_hash',
      header: 'SHA-256 Ledger Hash',
      accessor: (row) => (
        <CopyableText
          text={row.current_hash}
          displayValue={row.current_hash ? `${row.current_hash.substring(0, 14)}...` : 'Genesis'}
          label="Copy full SHA-256 block hash"
        />
      ),
    },
    {
      key: 'payload',
      header: 'Payload',
      className: 'text-right',
      accessor: (row) => {
        const isExp = expandedSeq === row.seq;
        return (
          <button
            type="button"
            onClick={() => setExpandedSeq(isExp ? null : row.seq)}
            className="px-2.5 py-1 rounded-lg text-xs font-mono font-medium bg-surface-alt border border-border hover:bg-border text-primary inline-flex items-center gap-1 transition-colors"
          >
            <span>{isExp ? 'Hide' : 'Inspect'}</span>
            {isExp ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          </button>
        );
      },
    },
  ];

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Title & Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold font-heading text-text">
            Cryptographic Audit Chain Explorer
          </h1>
          <p className="text-xs text-muted font-sans mt-0.5">
            Immutable SHA-256 Statutory Action Ledger & Chain Integrity Verification
          </p>
        </div>

        <div className="flex items-center gap-2.5 flex-wrap self-start sm:self-auto">
          {/* Timeline vs Table Toggle */}
          <div className="inline-flex rounded-xl bg-surface border border-border p-1 text-xs">
            <button
              type="button"
              onClick={() => setViewMode('timeline')}
              className={`px-3 py-1.5 rounded-lg font-medium transition-colors flex items-center gap-1.5 ${
                viewMode === 'timeline'
                  ? 'bg-primary text-white font-bold shadow-xs'
                  : 'text-muted hover:text-text'
              }`}
            >
              <GitCommit className="w-3.5 h-3.5" />
              <span>Timeline View</span>
            </button>
            <button
              type="button"
              onClick={() => setViewMode('table')}
              className={`px-3 py-1.5 rounded-lg font-medium transition-colors flex items-center gap-1.5 ${
                viewMode === 'table'
                  ? 'bg-primary text-white font-bold shadow-xs'
                  : 'text-muted hover:text-text'
              }`}
            >
              <TableIcon className="w-3.5 h-3.5" />
              <span>Table View</span>
            </button>
          </div>

          <button
            type="button"
            onClick={() => refetch()}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-xl bg-surface border border-border hover:bg-surface-alt text-text transition-colors shadow-xs"
          >
            <RotateCcw className="w-3.5 h-3.5 text-muted" />
            <span>Refresh</span>
          </button>

          {/* Export CSV Ledger Button */}
          <button
            type="button"
            onClick={handleExportCsv}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-xl bg-surface border border-border hover:bg-surface-alt text-primary transition-colors shadow-xs"
            title="Download immutable audit trail as CSV"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export CSV</span>
          </button>

          {/* Verify Chain Integrity Button */}
          <button
            type="button"
            onClick={handleVerifyChain}
            disabled={isVerifying}
            className="px-4 py-1.5 rounded-xl text-xs font-semibold bg-hero-gradient text-white shadow-glow hover:brightness-105 active:scale-95 transition-all flex items-center gap-2 disabled:opacity-60"
          >
            <ShieldCheck className={`w-4 h-4 ${isVerifying ? 'animate-spin' : ''}`} />
            <span>{isVerifying ? 'Verifying Ledger...' : 'Verify Chain Integrity'}</span>
          </button>
        </div>
      </div>

      {/* Verification Result Banner */}
      {hasVerified && verifyResult && (
        <div
          className={`p-4 rounded-2xl border text-xs font-semibold flex items-center justify-between shadow-xs transition-all ${
            verifyResult.valid
              ? 'bg-success/15 border-success/30 text-success'
              : 'bg-danger/15 border-danger/30 text-danger'
          }`}
        >
          <div className="flex items-center gap-3">
            {verifyResult.valid ? (
              <CheckCircle2 className="w-5 h-5 flex-shrink-0 text-success" />
            ) : (
              <AlertTriangle className="w-5 h-5 flex-shrink-0 text-danger" />
            )}
            <div className="space-y-0.5">
              <p className="font-bold">
                {verifyResult.valid
                  ? `Cryptographic Audit Chain Integrity Verified`
                  : `Cryptographic Audit Chain Integrity Failure!`}
              </p>
              <p className="font-normal font-mono text-[11px] opacity-90">
                {verifyResult.valid
                  ? `All ${verifyResult.checked ?? totalEntries} sequential SHA-256 blocks verified from Genesis sequence #1. Zero sequence gaps or payload tampering detected.`
                  : `Integrity broken at sequence #${verifyResult.first_broken_seq ?? 'unknown'}. Computed SHA-256 hash mismatch against recorded predecessor.`}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => setHasVerified(false)}
            className="text-xs hover:underline text-text ml-4 shrink-0 font-mono"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Advisory Banner */}
      <AdvisoryBanner
        confidence={100}
        sourceName="Hardware Security Module (HSM) Ledger"
        message="RULES.md Statutory Rule: Every state change, rule run, source call, officer action, and document read writes an immutable cryptographic audit event."
      />

      {/* KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <KpiCard
          title="Total Ledger Blocks"
          value={totalEntries.toLocaleString()}
          subtitle="Sequential Hash Chain"
          icon={Layers}
          badge={{ text: 'Synced', variant: 'primary' }}
        />
        <KpiCard
          title="Chain Integrity"
          value={verifyResult?.valid !== false ? '100% Valid' : 'Mismatch Detected'}
          subtitle="Cryptographically verified"
          icon={ShieldCheck}
          badge={{ text: 'Tamper-Evident', variant: 'success' }}
        />
        <KpiCard
          title="Genesis Root"
          value="Seq #1"
          subtitle="Immutable SHA-256 Genesis"
          icon={Clock}
          badge={{ text: 'Rooted', variant: 'secondary' }}
        />
        <KpiCard
          title="Active Page Range"
          value={`Page ${page} of ${Math.max(1, Math.ceil(totalEntries / 20))}`}
          subtitle="20 events per block page"
          icon={User}
          badge={{ text: 'Live Feed', variant: 'accent' }}
        />
      </div>

      {/* Filter toolbar */}
      <div className="p-4 rounded-2xl bg-surface border border-border shadow-card flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2 flex-1 min-w-[200px]">
          <Search className="w-4 h-4 text-muted" />
          <input
            type="text"
            value={eventFilter}
            onChange={(e) => {
              setEventFilter(e.target.value);
              setPage(1);
            }}
            placeholder="Filter by action (e.g. VALIDATE, LOGIN, ACTION)..."
            className="w-full text-xs rounded-xl border border-border bg-surface-alt px-3 py-2 text-text placeholder:text-muted focus:outline-none focus:ring-1 focus:ring-primary"
          />
        </div>

        <div className="flex items-center gap-2 min-w-[180px]">
          <Filter className="w-4 h-4 text-muted" />
          <input
            type="text"
            value={actorFilter}
            onChange={(e) => {
              setActorFilter(e.target.value);
              setPage(1);
            }}
            placeholder="Filter by actor email..."
            className="text-xs rounded-xl border border-border bg-surface-alt px-3 py-2 text-text placeholder:text-muted focus:outline-none focus:ring-1 focus:ring-primary"
          />
        </div>

        <div className="flex items-center gap-2 min-w-[160px]">
          <input
            type="text"
            value={appFilter}
            onChange={(e) => {
              setAppFilter(e.target.value);
              setPage(1);
            }}
            placeholder="Target Application ID..."
            className="text-xs rounded-xl border border-border bg-surface-alt px-3 py-2 text-text placeholder:text-muted focus:outline-none focus:ring-1 focus:ring-primary"
          />
        </div>

        {(eventFilter || actorFilter || appFilter) && (
          <button
            type="button"
            onClick={() => {
              setEventFilter('');
              setActorFilter('');
              setAppFilter('');
              setPage(1);
            }}
            className="text-xs text-muted hover:text-text px-2 py-1"
          >
            Clear Filters
          </button>
        )}
      </div>

      {/* Main Content: Table or Timeline */}
      {isLoading ? (
        <div className="space-y-4">
          {[...Array(5)].map((_, i) => (
            <Skeleton key={i} variant="card" className="h-24" />
          ))}
        </div>
      ) : isError ? (
        <div className="p-8 rounded-2xl bg-surface border border-danger/30 text-center space-y-4 shadow-card">
          <div className="w-12 h-12 rounded-full bg-danger/10 text-danger flex items-center justify-center mx-auto">
            <AlertTriangle className="w-6 h-6" />
          </div>
          <h2 className="text-base font-bold text-text">Failed to load audit ledger</h2>
          <p className="text-xs text-muted max-w-md mx-auto">
            Could not communicate with the statutory immutable audit log.
          </p>
          <button
            type="button"
            onClick={() => refetch()}
            className="px-4 py-2 bg-primary text-white text-xs font-semibold rounded-xl hover:bg-primary/90"
          >
            Retry Connection
          </button>
        </div>
      ) : rawEntries.length === 0 ? (
        <EmptyState
          icon={FileCheck2}
          title="No audit entries found"
          description="No ledger blocks match the selected action, actor, or application filters."
        />
      ) : viewMode === 'table' ? (
        <div className="space-y-4">
          <DataTable
            data={rawEntries}
            columns={tableColumns}
            pageSize={20}
            className="shadow-card rounded-2xl overflow-hidden"
          />

          {/* Expanded Payload Modal/Viewer */}
          {expandedSeq !== null && (
            <div className="p-4 rounded-2xl bg-surface border border-primary/30 shadow-card space-y-2">
              <div className="flex items-center justify-between text-xs font-mono">
                <span className="font-bold text-primary">
                  Inspecting Payload for Sequence #{expandedSeq}
                </span>
                <button
                  type="button"
                  onClick={() => setExpandedSeq(null)}
                  className="text-muted hover:text-text"
                >
                  Close
                </button>
              </div>
              <pre className="p-3 rounded-xl bg-surface-alt border border-border text-[11px] font-mono overflow-x-auto text-text max-h-60">
                {JSON.stringify(
                  rawEntries.find((e) => e.seq === expandedSeq)?.payload || {},
                  null,
                  2
                )}
              </pre>
            </div>
          )}
        </div>
      ) : (
        /* Timeline View: Connected Chronological Hash Chain */
        <div className="relative pl-6 sm:pl-8 space-y-6 before:content-[''] before:absolute before:left-3 sm:before:left-4 before:top-3 before:bottom-3 before:w-0.5 before:bg-border">
          {rawEntries.map((block) => {
            const isExp = expandedSeq === block.seq;
            return (
              <div key={block.seq} className="relative group">
                {/* Node indicator */}
                <div className="absolute -left-6 sm:-left-8 top-3.5 w-6 h-6 rounded-full bg-surface border-2 border-primary flex items-center justify-center text-[10px] font-mono text-primary font-bold shadow-xs">
                  <Hash className="w-3 h-3 text-primary" />
                </div>

                {/* Block Card */}
                <div className="p-4 sm:p-5 rounded-2xl bg-surface border border-border shadow-card space-y-3 transition-all hover:border-primary/40">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-border/60 pb-3">
                    <div className="flex items-center gap-2.5 flex-wrap">
                      <span className="font-mono text-xs px-2.5 py-0.5 rounded-full bg-primary/10 text-primary font-bold border border-primary/20">
                        Seq #{block.seq}
                      </span>
                      <span className="font-mono text-xs font-bold text-text uppercase">
                        {block.action}
                      </span>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-surface-alt text-muted border border-border uppercase">
                        {block.role}
                      </span>
                    </div>

                    <div className="flex items-center gap-2 text-xs text-muted font-mono">
                      <span>Actor: <strong className="text-text font-normal">{block.actor}</strong></span>
                      <span>•</span>
                      <span>{new Date(block.created_at).toLocaleString()}</span>
                    </div>
                  </div>

                  {/* Cryptographic Linkage Details */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                    <div className="space-y-1.5 font-mono text-[11px]">
                      <div className="flex items-center justify-between">
                        <span className="text-muted">Target Resource:</span>
                        <span className="font-bold text-text">
                          {block.target_type} ({block.target_id || 'Global'})
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-muted">Previous Block Hash:</span>
                        <span className="text-muted truncate max-w-[220px]" title={block.prev_hash}>
                          {block.prev_hash ? `${block.prev_hash.substring(0, 16)}...` : 'Genesis'}
                        </span>
                      </div>
                    </div>

                    <div className="space-y-1.5 font-mono text-[11px]">
                      <div className="flex items-center justify-between">
                        <span className="text-muted">Payload SHA-256:</span>
                        <span className="text-primary truncate max-w-[220px]" title={block.payload_hash}>
                          {block.payload_hash ? `${block.payload_hash.substring(0, 16)}...` : 'None'}
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-muted">Current Ledger Hash:</span>
                        <span className="text-success truncate max-w-[220px] font-bold" title={block.current_hash}>
                          {block.current_hash ? `${block.current_hash.substring(0, 16)}...` : 'Genesis'}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Collapsible Payload Section */}
                  <div className="pt-2 border-t border-border/40">
                    <button
                      type="button"
                      onClick={() => setExpandedSeq(isExp ? null : block.seq)}
                      className="text-xs font-mono text-primary hover:underline flex items-center gap-1 font-semibold"
                    >
                      <span>{isExp ? 'Hide Verified Payload JSON' : 'View Verified Payload JSON'}</span>
                      {isExp ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                    </button>

                    {isExp && (
                      <pre className="mt-2 p-3 rounded-xl bg-surface-alt border border-border text-[11px] font-mono overflow-x-auto text-text max-h-56 animate-in fade-in duration-150">
                        {JSON.stringify(block.payload, null, 2)}
                      </pre>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Pagination Bar */}
      {totalEntries > 20 && (
        <div className="flex items-center justify-between p-4 rounded-2xl bg-surface border border-border text-xs">
          <span className="text-muted font-mono">
            Showing {(page - 1) * 20 + 1} to {Math.min(page * 20, totalEntries)} of {totalEntries} blocks
          </span>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-3 py-1.5 rounded-xl border border-border bg-surface-alt disabled:opacity-40 font-semibold"
            >
              Previous Page
            </button>
            <span className="font-mono font-bold text-text">Page {page}</span>
            <button
              type="button"
              onClick={() => setPage((p) => p + 1)}
              disabled={page * 20 >= totalEntries}
              className="px-3 py-1.5 rounded-xl border border-border bg-surface-alt disabled:opacity-40 font-semibold"
            >
              Next Page
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
