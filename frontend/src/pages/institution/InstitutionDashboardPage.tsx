import { useNavigate } from 'react-router-dom';
import {
  FileText,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Plus,
  ChevronRight,
  RotateCcw,
} from 'lucide-react';
import { useApplications } from '../../api/useApplications';
import { useAlerts } from '../../api/useAlerts';
import { KpiCard } from '../../components/KpiCard';
import { DataTable, Column } from '../../components/DataTable';
import { StatusChip } from '../../components/StatusChip';
import { AdvisoryBanner } from '../../components/AdvisoryBanner';
import { TableSkeleton } from '../../components/Skeleton';
import { EmptyState } from '../../components/EmptyState';
import { CopyableText } from '../../components/CopyableText';
import { useAuth } from '../../context/AuthContext';

export default function InstitutionDashboardPage() {
  const navigate = useNavigate();
  const { user } = useAuth();

  const {
    data: applicationsData,
    isLoading: isAppsLoading,
    isError: isAppsError,
    refetch: refetchApps,
  } = useApplications();

  const { data: alertsData } = useAlerts();

  const applications = applicationsData?.items || [];
  const totalApps = applicationsData?.total ?? applications.length;
  const deficiencyCount = applications.reduce((acc, app) => acc + (app.deficiency_count || 0), 0);
  const unreadAlerts = alertsData?.items?.filter((a) => !a.acknowledged) || [];

  const columns: Column<any>[] = [
    {
      key: 'id',
      header: 'Application Ref ID',
      sortable: true,
      accessor: (row) => (
        <CopyableText text={row.id} label="Copy Application Ref ID" />
      ),
    },
    {
      key: 'program_name',
      header: 'Academic Program',
      sortable: true,
      accessor: (row) => (
        <span className="font-medium text-text">
          {row.program_name || 'Engineering & Technology (UG/PG)'}
        </span>
      ),
    },
    {
      key: 'academic_year',
      header: 'Cycle',
      accessor: (row) => <span className="font-mono text-muted">{row.academic_year}</span>,
    },
    {
      key: 'state',
      header: 'Statutory State',
      accessor: (row) => <StatusChip status={row.state} />,
    },
    {
      key: 'deficiency_count',
      header: 'Rectifications',
      accessor: (row) =>
        (row.deficiency_count || 0) > 0 ? (
          <span className="px-2 py-0.5 rounded-full text-xs font-mono font-bold bg-warning/15 text-warning border border-warning/30">
            {row.deficiency_count} Actionable
          </span>
        ) : (
          <span className="text-success text-xs font-medium">Clear</span>
        ),
    },
    {
      key: 'created_at',
      header: 'Submitted Date',
      accessor: (row) => (
        <span className="font-mono text-xs text-muted">
          {row.submitted_at || row.created_at
            ? new Date(row.submitted_at || row.created_at).toLocaleDateString()
            : 'Draft'}
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
          onClick={() => navigate(`/institution/applications/${row.id}`)}
          className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-surface-alt hover:bg-border text-primary border border-border inline-flex items-center gap-1 transition-colors"
        >
          <span>Open Dossier</span>
          <ChevronRight className="w-3.5 h-3.5" />
        </button>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Title & Top Action */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold font-heading text-text">
            Institutional Scrutiny Dashboard
          </h1>
          <p className="text-xs text-muted font-sans mt-0.5">
            {user?.full_name || 'Higher Education Institution'} • PID: {user?.institution_id || '1-0028912'}
          </p>
        </div>

        <button
          type="button"
          onClick={() => navigate('/institution/submit')}
          className="px-4 py-2.5 rounded-xl font-heading font-bold text-xs bg-hero-gradient text-white shadow-glow hover:brightness-105 active:scale-95 transition-all flex items-center gap-2 self-start sm:self-auto"
        >
          <Plus className="w-4 h-4" />
          <span>New EoA Application</span>
        </button>
      </div>

      {/* Advisory Banner */}
      <AdvisoryBanner
        confidence={98.5}
        sourceName="AICTE Central Portal"
        message="Extension of Approval window closes on November 30. Please ensure all requested clarifications and land certificates are uploaded before statutory review."
      />

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          title="Active Applications"
          value={totalApps}
          subtitle="Cycle 2026-27"
          icon={FileText}
          badge={{ text: 'In Progress', variant: 'primary' }}
        />
        <KpiCard
          title="Actionable Deficiencies"
          value={deficiencyCount}
          subtitle="Rectifications required"
          icon={AlertTriangle}
          badge={{ text: deficiencyCount > 0 ? 'Action Needed' : 'Clear', variant: deficiencyCount > 0 ? 'warning' : 'success' }}
        />
        <KpiCard
          title="Active Notifications"
          value={unreadAlerts.length}
          subtitle="Statutory alerts"
          icon={Clock}
          badge={{ text: `${unreadAlerts.length} Alerts`, variant: 'accent' }}
        />
        <KpiCard
          title="Compliance Health"
          value="Good"
          subtitle="All documents verified"
          icon={CheckCircle2}
          badge={{ text: 'Healthy', variant: 'success' }}
        />
      </div>

      {/* Applications Data Table */}
      <div className="space-y-3">
        <h2 className="text-sm font-bold font-heading text-text">
          Extension of Approval Applications
        </h2>

        {isAppsLoading ? (
          <div className="rounded-card bg-surface border border-border p-5 shadow-card">
            <TableSkeleton rows={4} cols={6} />
          </div>
        ) : isAppsError ? (
          <div className="rounded-card bg-surface border border-danger/30 p-8 text-center space-y-3 shadow-card">
            <AlertTriangle className="w-8 h-8 text-danger mx-auto" />
            <h4 className="text-sm font-bold text-text">Failed to load applications</h4>
            <p className="text-xs text-muted max-w-sm mx-auto">
              Unable to reach statutory intake endpoints. Please verify network connectivity.
            </p>
            <button
              type="button"
              onClick={() => refetchApps()}
              className="px-4 py-2 rounded-xl text-xs font-semibold bg-primary text-white inline-flex items-center gap-1.5"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Retry Request</span>
            </button>
          </div>
        ) : applications.length === 0 ? (
          <EmptyState
            title="No Applications Found"
            description="Your institution has not initiated an Extension of Approval application for this academic cycle."
            actionText="Start New EoA Application"
            onAction={() => navigate('/institution/submit')}
          />
        ) : (
          <DataTable
            data={applications}
            columns={columns}
            searchPlaceholder="Search by Application Ref ID or program name..."
          />
        )}
      </div>
    </div>
  );
}
