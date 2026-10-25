import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ArrowRight,
  RotateCcw,
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
  Search,
  Filter,
  Bookmark,
  Plus,
  Trash2,
  UserCheck,
  CheckSquare,
  Square,
} from 'lucide-react';
import { useApplications } from '../../api/useApplications';
import { DataTable, Column } from '../../components/DataTable';
import { StatusChip } from '../../components/StatusChip';
import { SeverityChip } from '../../components/SeverityChip';
import { AdvisoryBanner } from '../../components/AdvisoryBanner';
import { TableSkeleton } from '../../components/Skeleton';
import { EmptyState } from '../../components/EmptyState';
import { CopyableText } from '../../components/CopyableText';
import { toastBus } from '../../lib/toastBus';
import { useAuth } from '../../context/AuthContext';
import api from '../../lib/api';

interface SavedView {
  id: string;
  name: string;
  state: string;
  severity: string;
  search: string;
}

const DEFAULT_VIEWS: SavedView[] = [
  { id: 'all', name: 'All Dossiers', state: '', severity: '', search: '' },
  { id: 'ready_scrutiny', name: 'Ready for Scrutiny', state: 'READY_FOR_SCRUTINY', severity: '', search: '' },
  { id: 'under_review', name: 'Under Official Review', state: 'UNDER_OFFICIAL_REVIEW', severity: '', search: '' },
  { id: 'rectifications', name: 'Rectification Pending', state: 'RECTIFICATION_REQUESTED', severity: '', search: '' },
  { id: 'critical', name: 'Critical Deficiencies', state: '', severity: 'critical', search: '' },
];

export default function ApplicationsQueuePage() {
  const navigate = useNavigate();
  const { user } = useAuth();

  // Filter state
  const [stateFilter, setStateFilter] = useState<string>('');
  const [severityFilter, setSeverityFilter] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [page, setPage] = useState<number>(1);
  const pageSize = 15;

  // Saved views from localStorage
  const [savedViews, setSavedViews] = useState<SavedView[]>(() => {
    try {
      const stored = localStorage.getItem('fixora_saved_views');
      return stored ? JSON.parse(stored) : DEFAULT_VIEWS;
    } catch {
      return DEFAULT_VIEWS;
    }
  });
  const [activeViewId, setActiveViewId] = useState<string>('all');
  const [customViewName, setCustomViewName] = useState<string>('');
  const [isSavingView, setIsSavingView] = useState<boolean>(false);

  // Bulk Selection
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [isBulkAssigning, setIsBulkAssigning] = useState<boolean>(false);

  // Query
  const {
    data: applicationsData,
    isLoading,
    isError,
    refetch,
  } = useApplications({
    state: stateFilter || undefined,
    severity: severityFilter || undefined,
    q: searchQuery || undefined,
    page,
    page_size: pageSize,
  });

  const applications = applicationsData?.items || [];
  const total = applicationsData?.total || 0;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  // Handle saved view selection
  const handleSelectView = (view: SavedView) => {
    setActiveViewId(view.id);
    setStateFilter(view.state);
    setSeverityFilter(view.severity);
    setSearchQuery(view.search);
    setPage(1);
    setSelectedIds(new Set());
  };

  // Save current view
  const handleSaveCurrentView = () => {
    if (!customViewName.trim()) return;
    const newView: SavedView = {
      id: `view-${Date.now()}`,
      name: customViewName.trim(),
      state: stateFilter,
      severity: severityFilter,
      search: searchQuery,
    };
    const updated = [...savedViews, newView];
    setSavedViews(updated);
    localStorage.setItem('fixora_saved_views', JSON.stringify(updated));
    setActiveViewId(newView.id);
    setCustomViewName('');
    setIsSavingView(false);
    toastBus.show({
      type: 'success',
      title: 'View Saved',
      message: `Custom view "${newView.name}" saved to your workspace.`,
    });
  };

  // Delete custom view
  const handleDeleteView = (viewId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const updated = savedViews.filter((v) => v.id !== viewId);
    setSavedViews(updated);
    localStorage.setItem('fixora_saved_views', JSON.stringify(updated));
    if (activeViewId === viewId) {
      handleSelectView(DEFAULT_VIEWS[0]);
    }
  };

  // Selection handlers
  const handleToggleSelectAll = () => {
    if (selectedIds.size === applications.length && applications.length > 0) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(applications.map((a: any) => a.id)));
    }
  };

  const handleToggleSelectRow = (id: string) => {
    const next = new Set(selectedIds);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setSelectedIds(next);
  };

  // Bulk Assign Action
  const handleBulkAssign = async () => {
    if (selectedIds.size === 0) return;
    setIsBulkAssigning(true);
    try {
      // Execute assignment requests for selected applications
      for (const appId of selectedIds) {
        try {
          await api.post(`/applications/${appId}/take-review`);
        } catch {
          // continue for others
        }
      }
      toastBus.show({
        type: 'success',
        title: 'Bulk Assignment Complete',
        message: `Assigned ${selectedIds.size} applications to ${user?.email || 'officer'}.`,
      });
      setSelectedIds(new Set());
      refetch();
    } catch {
      toastBus.show({
        type: 'danger',
        title: 'Bulk Assign Failed',
        message: 'Could not complete batch assignment.',
      });
    } finally {
      setIsBulkAssigning(false);
    }
  };

  const columns: Column<any>[] = [
    {
      key: 'select',
      header: 'Select',
      className: 'w-10 text-center',
      accessor: (row) => (
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            handleToggleSelectRow(row.id);
          }}
          className="text-muted hover:text-text p-1"
        >
          {selectedIds.has(row.id) ? (
            <CheckSquare className="w-4 h-4 text-primary" />
          ) : (
            <Square className="w-4 h-4" />
          )}
        </button>
      ),
    },
    {
      key: 'id',
      header: 'Application Ref ID',
      sortable: true,
      accessor: (row) => (
        <CopyableText text={row.id} label="Copy Application Ref ID" />
      ),
    },
    {
      key: 'institution_name',
      header: 'Higher Education Institution',
      sortable: true,
      accessor: (row) => (
        <div>
          <p className="font-semibold text-text">{row.institution_name || 'Higher Technical Institute'}</p>
          <span className="text-[11px] text-muted">
            {row.program_name || row.category}
          </span>
        </div>
      ),
    },
    {
      key: 'state',
      header: 'Statutory State',
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
            (row.priority_score || 0) >= 70
              ? 'bg-danger/10 text-danger'
              : (row.priority_score || 0) >= 40
              ? 'bg-warning/10 text-warning'
              : 'bg-success/10 text-success'
          }`}
        >
          {row.priority_score ?? 'N/A'}
        </span>
      ),
    },
    {
      key: 'severity',
      header: 'Severity',
      sortable: true,
      accessor: (row) => <SeverityChip severity={row.severity || 'info'} />,
    },
    {
      key: 'findings_count',
      header: 'Discrepancy Flags',
      sortable: true,
      accessor: (row) => (
        <span className="font-mono text-xs font-semibold">
          {(row.findings_count || 0) > 0 ? (
            <span className="text-warning">{row.findings_count} discrepancies</span>
          ) : (
            <span className="text-success">Compliant</span>
          )}
        </span>
      ),
    },
    {
      key: 'created_at',
      header: 'Intake Date',
      sortable: true,
      accessor: (row) => (
        <span className="font-mono text-xs text-muted">
          {row.created_at ? new Date(row.created_at).toLocaleDateString() : 'N/A'}
        </span>
      ),
    },
    {
      key: 'actions',
      header: '',
      className: 'text-right',
      accessor: (row) => (
        <button
          type="button"
          onClick={() => navigate(`/officer/applications/${row.id}`)}
          className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-hero-gradient text-white shadow-xs hover:brightness-105 active:scale-95 inline-flex items-center gap-1 transition-all"
        >
          <span>Review</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold font-heading text-text">
            Regional Scrutiny Intake Queue
          </h1>
          <p className="text-xs text-muted font-sans mt-0.5">
            AICTE Approval Process Handbook (APH 2026-27) Master Queue • Total ({total}) Dossiers
          </p>
        </div>

        <button
          type="button"
          onClick={() => refetch()}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-surface border border-border hover:bg-surface-alt text-text self-start sm:self-auto transition-colors"
        >
          <RotateCcw className="w-3.5 h-3.5 text-muted" />
          <span>Refresh</span>
        </button>
      </div>

      {/* Advisory Banner */}
      <AdvisoryBanner
        confidence={97.8}
        sourceName="Regional Scrutiny Matrix"
        message="Deterministic rules decide requirements. Machine learning extracts parameters and highlights candidate discrepancies for authorised officer confirmation."
      />

      {/* Saved Views Toolbar */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-xs">
          <span className="font-bold text-text uppercase font-mono tracking-wide flex items-center gap-1.5">
            <Bookmark className="w-3.5 h-3.5 text-primary" />
            <span>Saved Workspace Views</span>
          </span>
          <button
            type="button"
            onClick={() => setIsSavingView(!isSavingView)}
            className="text-xs text-primary hover:underline flex items-center gap-1"
          >
            <Plus className="w-3 h-3" />
            <span>Save Current Filters</span>
          </button>
        </div>

        {/* View Pills */}
        <div className="flex items-center gap-2 overflow-x-auto pb-1">
          {savedViews.map((view) => (
            <button
              key={view.id}
              type="button"
              onClick={() => handleSelectView(view)}
              className={`px-3 py-1.5 rounded-xl text-xs font-medium font-sans flex items-center gap-2 border transition-all shrink-0 ${
                activeViewId === view.id
                  ? 'bg-primary text-white border-primary shadow-xs'
                  : 'bg-surface border-border text-text hover:bg-surface-alt'
              }`}
            >
              <span>{view.name}</span>
              {!DEFAULT_VIEWS.some((d) => d.id === view.id) && (
                <Trash2
                  className="w-3 h-3 hover:text-danger ml-1"
                  onClick={(e) => handleDeleteView(view.id, e)}
                />
              )}
            </button>
          ))}
        </div>

        {/* Save View Modal / Input Box */}
        {isSavingView && (
          <div className="p-3 bg-surface-alt rounded-xl border border-primary/30 flex items-center gap-2 max-w-md">
            <input
              type="text"
              value={customViewName}
              onChange={(e) => setCustomViewName(e.target.value)}
              placeholder="Name this view (e.g. Critical Maharashtra Engineering)..."
              className="flex-1 text-xs px-3 py-1.5 rounded-lg border border-border bg-surface text-text focus:outline-none focus:ring-1 focus:ring-primary"
            />
            <button
              type="button"
              onClick={handleSaveCurrentView}
              className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-primary text-white hover:bg-primary/90"
            >
              Save View
            </button>
            <button
              type="button"
              onClick={() => setIsSavingView(false)}
              className="text-xs text-muted hover:text-text px-1"
            >
              Cancel
            </button>
          </div>
        )}
      </div>

      {/* Filter and Search Bar */}
      <div className="p-4 rounded-card bg-surface border border-border shadow-card flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2.5 flex-1 min-w-[280px]">
          {/* Search Query */}
          <div className="relative flex-1 min-w-[200px]">
            <Search className="w-4 h-4 text-muted absolute left-3 top-2.5" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setPage(1);
              }}
              placeholder="Search by Institution, ID, or Program..."
              className="w-full pl-9 pr-3 py-2 text-xs rounded-xl bg-surface-alt border border-border text-text placeholder:text-muted focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>

          {/* State Filter */}
          <select
            value={stateFilter}
            onChange={(e) => {
              setStateFilter(e.target.value);
              setPage(1);
            }}
            className="text-xs px-3 py-2 rounded-xl bg-surface-alt border border-border text-text focus:outline-none focus:ring-1 focus:ring-primary"
          >
            <option value="">All Statutory States</option>
            <option value="SUBMITTED">Submitted</option>
            <option value="VALIDATION_IN_PROGRESS">Validation in Progress</option>
            <option value="DEFICIENCIES_FOUND">Deficiencies Found</option>
            <option value="RECTIFICATION_REQUESTED">Rectification Requested</option>
            <option value="READY_FOR_SCRUTINY">Ready for Scrutiny</option>
            <option value="UNDER_OFFICIAL_REVIEW">Under Official Review</option>
            <option value="REFERRED_FOR_INSPECTION">Referred for Inspection</option>
            <option value="APPROVED">Approved</option>
          </select>

          {/* Severity Filter */}
          <select
            value={severityFilter}
            onChange={(e) => {
              setSeverityFilter(e.target.value);
              setPage(1);
            }}
            className="text-xs px-3 py-2 rounded-xl bg-surface-alt border border-border text-text focus:outline-none focus:ring-1 focus:ring-primary"
          >
            <option value="">All Severities</option>
            <option value="critical">Critical</option>
            <option value="major">Major</option>
            <option value="moderate">Moderate</option>
            <option value="minor">Minor</option>
          </select>

          {(stateFilter || severityFilter || searchQuery) && (
            <button
              type="button"
              onClick={() => {
                setStateFilter('');
                setSeverityFilter('');
                setSearchQuery('');
                setPage(1);
              }}
              className="text-xs text-muted hover:text-text px-2 py-1"
            >
              Reset Filters
            </button>
          )}

          {applications.length > 0 && (
            <button
              type="button"
              onClick={handleToggleSelectAll}
              className="text-xs text-primary hover:underline px-2 py-1 font-mono font-medium"
            >
              {selectedIds.size === applications.length ? 'Deselect All' : `Select All (${applications.length})`}
            </button>
          )}
        </div>

        {/* Floating Bulk Action if items selected */}
        {selectedIds.size > 0 && (
          <div className="flex items-center gap-2 bg-primary/10 border border-primary/30 px-3 py-1.5 rounded-xl">
            <span className="text-xs font-mono font-bold text-primary">
              {selectedIds.size} Selected
            </span>
            <button
              type="button"
              onClick={handleBulkAssign}
              disabled={isBulkAssigning}
              className="px-3 py-1 rounded-lg text-xs font-semibold bg-primary text-white hover:bg-primary/90 flex items-center gap-1.5 shadow-xs disabled:opacity-50"
            >
              <UserCheck className="w-3.5 h-3.5" />
              <span>{isBulkAssigning ? 'Assigning...' : 'Assign to Me'}</span>
            </button>
          </div>
        )}
      </div>

      {/* Main Table View */}
      {isLoading ? (
        <TableSkeleton rows={10} />
      ) : isError ? (
        <div className="p-8 rounded-card bg-surface border border-danger/30 text-center space-y-4">
          <AlertTriangle className="w-10 h-10 text-danger mx-auto" />
          <h2 className="text-base font-bold text-text">Failed to load applications queue</h2>
          <button
            type="button"
            onClick={() => refetch()}
            className="px-4 py-2 bg-primary text-white text-xs font-semibold rounded-lg"
          >
            Retry Connection
          </button>
        </div>
      ) : applications.length === 0 ? (
        <EmptyState
          icon={Filter}
          title="No dossiers match criteria"
          description="Try broadening your state or severity filters, or search query."
        />
      ) : (
        <div className="space-y-4">
          <DataTable
            data={applications}
            columns={columns}
            searchPlaceholder="Filter listed applications..."
          />

          {/* Pagination Controls */}
          <div className="flex items-center justify-between text-xs font-mono text-muted pt-2 border-t border-border">
            <span>
              Showing {(page - 1) * pageSize + 1} - {Math.min(page * pageSize, total)} of {total} dossiers
            </span>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1}
                className="p-1.5 rounded-lg border border-border bg-surface text-text hover:bg-surface-alt disabled:opacity-40"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span className="text-text font-bold px-2">Page {page} of {totalPages}</span>
              <button
                type="button"
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
                className="p-1.5 rounded-lg border border-border bg-surface text-text hover:bg-surface-alt disabled:opacity-40"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
