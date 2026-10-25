import { useNavigate } from 'react-router-dom';
import {
  Plus,
  Code,
  AlertTriangle,
  RotateCcw,
  Layers,
} from 'lucide-react';
import { DataTable, Column } from '../../components/DataTable';
import { AdvisoryBanner } from '../../components/AdvisoryBanner';
import { Skeleton } from '../../components/Skeleton';
import { EmptyState } from '../../components/EmptyState';
import { useRulePacks, RulePackItem } from '../../api';

export default function RulePacksPage() {
  const navigate = useNavigate();
  const { data, isLoading, isError, refetch } = useRulePacks();

  const items = (data?.items || []) as unknown as RulePackItem[];

  const columns: Column<RulePackItem>[] = [
    {
      key: 'id',
      header: 'Rule Pack ID',
      sortable: true,
      accessor: (row) => (
        <span className="font-mono font-bold text-primary">{row.id}</span>
      ),
    },
    {
      key: 'name',
      header: 'Rule Specification Name',
      sortable: true,
      accessor: (row) => (
        <div>
          <p className="font-semibold text-text">{row.name}</p>
          <span className="text-[11px] font-sans text-muted truncate max-w-xs block">
            {row.description || 'Statutory AICTE APH Rule Configuration'}
          </span>
        </div>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      sortable: true,
      accessor: (row) => {
        const isDraft = row.status?.toLowerCase() === 'draft';
        return (
          <span
            className={`px-2 py-0.5 rounded-full text-[11px] font-mono font-bold uppercase border ${
              isDraft
                ? 'bg-warning/15 text-warning border-warning/30'
                : 'bg-success/15 text-success border-success/30'
            }`}
          >
            {row.status}
          </span>
        );
      },
    },
    {
      key: 'versions',
      header: 'Versions',
      accessor: (row) => {
        const vers = (row as any).versions || [];
        const activeVer = vers.find((v: any) => v.is_active) || vers[0];
        return (
          <div className="flex items-center gap-1.5 flex-wrap">
            {activeVer && (
              <span className="font-mono text-xs px-2 py-0.5 rounded bg-surface-alt border border-border">
                {activeVer.version} {activeVer.is_active ? '(Active)' : ''}
              </span>
            )}
            <span className="text-[11px] text-muted">
              ({vers.length} {vers.length === 1 ? 'version' : 'versions'})
            </span>
          </div>
        );
      },
    },
    {
      key: 'actions',
      header: 'Actions',
      className: 'text-right',
      accessor: (row) => (
        <button
          type="button"
          onClick={() => navigate(`/admin/rules/${row.id}`)}
          className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-surface-alt hover:bg-border text-primary border border-border inline-flex items-center gap-1.5 transition-colors"
        >
          <Code className="w-3.5 h-3.5" />
          <span>Edit in IDE</span>
        </button>
      ),
    },
  ];

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton variant="card" className="h-20" />
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
        <h2 className="text-base font-bold text-text">Failed to load rule packs</h2>
        <p className="text-xs text-muted max-w-md mx-auto">
          Could not communicate with the statutory rule pack service.
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
            Deterministic Rule Packs Registry
          </h1>
          <p className="text-xs text-muted font-sans mt-0.5">
            YAML Rule Specifications, Maker-Checker Governance, and APH Clause Mappings
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => refetch()}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-surface border border-border hover:bg-surface-alt text-text transition-colors"
          >
            <RotateCcw className="w-3.5 h-3.5 text-muted" />
            Refresh
          </button>
          <button
            type="button"
            onClick={() => navigate('/admin/rules/new')}
            className="px-4 py-1.5 rounded-lg text-xs font-bold font-heading bg-hero-gradient text-white shadow-glow hover:brightness-105 active:scale-95 transition-all flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            <span>New Rule Pack</span>
          </button>
        </div>
      </div>

      {/* Advisory Banner */}
      <AdvisoryBanner
        confidence={100}
        sourceName="Statutory Rule Engine"
        message="RULES.md Principle: Rules are data (YAML), not code. Deterministic rules decide statutory compliance; ML models extract and flag parameters."
      />

      {/* Table */}
      {items.length === 0 ? (
        <EmptyState
          icon={Layers}
          title="No Rule Packs Configured"
          description="Create your first YAML-based statutory rule pack to enable automated checklist evaluation."
        />
      ) : (
        <DataTable
          data={items}
          columns={columns}
          searchPlaceholder="Search rule packs by ID, title, or clause..."
        />
      )}
    </div>
  );
}
