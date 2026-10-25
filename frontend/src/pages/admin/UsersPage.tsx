import { useState } from 'react';
import {
  Users,
  Shield,
  Building2,
  Search,
  Filter,
  UserCheck,
  Copy,
  Check,
} from 'lucide-react';
import { AdvisoryBanner } from '../../components/AdvisoryBanner';
import { Role } from '../../lib/vocab';

interface SeededUser {
  id: string;
  email: string;
  full_name: string;
  role: Role;
  role_label: string;
  institution_id: string | null;
  institution_name: string | null;
  is_active: boolean;
  department: string;
}

const SEEDED_SYSTEM_USERS: SeededUser[] = [
  {
    id: 'USR-001',
    email: 'admin@aicte.gov.in',
    full_name: 'AICTE System Administrator',
    role: 'admin',
    role_label: 'System Administrator',
    institution_id: null,
    institution_name: 'AICTE Headquarters (New Delhi)',
    is_active: true,
    department: 'Policy, IT & Statutory Governance Bureau',
  },
  {
    id: 'USR-002',
    email: 'scrutiny@aicte.gov.in',
    full_name: 'Dr. Ramesh Chandra (Scrutiny Bureau)',
    role: 'scrutiny_officer',
    role_label: 'Scrutiny Officer',
    institution_id: null,
    institution_name: 'AICTE Western Regional Office (WRO)',
    is_active: true,
    department: 'Approval Process Bureau (Scrutiny Division)',
  },
  {
    id: 'USR-003',
    email: 'verification@aicte.gov.in',
    full_name: 'Smt. Sunita Rao (Verification Bureau)',
    role: 'verification_officer',
    role_label: 'Verification Officer',
    institution_id: null,
    institution_name: 'AICTE South-Western Regional Office',
    is_active: true,
    department: 'Statutory Verification & Registry Bureau',
  },
  {
    id: 'USR-004',
    email: 'principal@gecpune.edu.in',
    full_name: 'Prof. D. K. Deshmukh (Principal, GEC Pune)',
    role: 'institution',
    role_label: 'Institutional Applicant',
    institution_id: '1-33276541',
    institution_name: 'Government College of Engineering, Pune',
    is_active: true,
    department: 'College Directorate & Regulatory Affairs',
  },
  {
    id: 'USR-005',
    email: 'director@mitmumbai.edu.in',
    full_name: 'Dr. V. N. Patil (Director, MIT Mumbai)',
    role: 'institution',
    role_label: 'Institutional Applicant',
    institution_id: '1-44589210',
    institution_name: 'Maharashtra Institute of Technology, Mumbai',
    is_active: true,
    department: 'Institutional Governance',
  },
  {
    id: 'USR-006',
    email: 'principal@kitmblr.edu.in',
    full_name: 'Dr. A. K. Narayan (Principal, KITM Bengaluru)',
    role: 'institution',
    role_label: 'Institutional Applicant',
    institution_id: '1-55691023',
    institution_name: 'Karnataka Institute of Technology & Management, Bengaluru',
    is_active: true,
    department: 'Office of the Principal',
  },
  {
    id: 'USR-007',
    email: 'director@ncphyderabad.edu.in',
    full_name: 'Dr. Priya Reddy (Director, NCP Hyderabad)',
    role: 'institution',
    role_label: 'Institutional Applicant',
    institution_id: '1-66782345',
    institution_name: 'National College of Pharmacy, Hyderabad',
    is_active: true,
    department: 'Pharmacy Education Directorate',
  },
  {
    id: 'USR-008',
    email: 'dean@daapdelhi.edu.in',
    full_name: 'Prof. Sanjay Malhotra (Dean, DAAP New Delhi)',
    role: 'institution',
    role_label: 'Institutional Applicant',
    institution_id: '1-77893456',
    institution_name: 'Delhi Academy of Architecture & Planning, New Delhi',
    is_active: true,
    department: 'Architecture & Planning Faculty',
  },
];

export default function UsersPage() {
  const [searchTerm, setSearchTerm] = useState('');
  const [roleFilter, setRoleFilter] = useState<string>('all');
  const [copiedEmail, setCopiedEmail] = useState<string | null>(null);

  const filteredUsers = SEEDED_SYSTEM_USERS.filter((u) => {
    const matchesSearch =
      u.full_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      u.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (u.institution_name && u.institution_name.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (u.institution_id && u.institution_id.includes(searchTerm));

    const matchesRole = roleFilter === 'all' || u.role === roleFilter;

    return matchesSearch && matchesRole;
  });

  const handleCopyEmail = (email: string) => {
    navigator.clipboard.writeText(email);
    setCopiedEmail(email);
    setTimeout(() => setCopiedEmail(null), 2500);
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Title */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold font-heading text-text flex items-center gap-2">
            <Users className="w-6 h-6 text-primary" />
            Statutory Users & Access Governance
          </h1>
          <p className="text-xs text-muted font-sans mt-0.5">
            Role-Based Access Control (RBAC) Directory: Seeded Council Officials & Institutional Representatives
          </p>
        </div>

        <span className="text-xs font-mono text-muted bg-surface px-3 py-1.5 rounded-xl border border-border shadow-xs self-start sm:self-auto">
          Read-Only Statutory Directory (Seeded Environment)
        </span>
      </div>

      {/* Advisory Banner */}
      <AdvisoryBanner
        confidence={100}
        sourceName="Statutory IAM Bureau"
        message="Dual-authorization maker-checker rules enforce strict role boundaries. Institution users are isolated strictly to their designated permanent institution ID (PID)."
      />

      {/* Search & Filter Toolbar */}
      <div className="p-4 rounded-2xl bg-surface border border-border shadow-card flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 flex-1 min-w-[240px]">
          <Search className="w-4 h-4 text-muted" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search by name, email, PID, or institution..."
            className="w-full text-xs rounded-xl border border-border bg-surface-alt px-3 py-2 text-text placeholder:text-muted focus:outline-none focus:ring-1 focus:ring-primary"
          />
        </div>

        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-muted" />
          <select
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value)}
            className="text-xs rounded-xl border border-border bg-surface-alt px-3 py-2 text-text font-semibold focus:outline-none focus:ring-1 focus:ring-primary"
          >
            <option value="all">All Roles (8 Seeded)</option>
            <option value="admin">System Admin</option>
            <option value="scrutiny_officer">Scrutiny Officer</option>
            <option value="verification_officer">Verification Officer</option>
            <option value="institution">Institution (PID)</option>
          </select>
        </div>
      </div>

      {/* User Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {filteredUsers.map((u) => {
          const isCopied = copiedEmail === u.email;
          const roleBadgeColor =
            u.role === 'admin'
              ? 'bg-primary/15 text-primary border-primary/30'
              : u.role === 'scrutiny_officer'
              ? 'bg-secondary/15 text-secondary border-secondary/30'
              : u.role === 'verification_officer'
              ? 'bg-accent/15 text-accent border-accent/30'
              : 'bg-success/15 text-success border-success/30';

          return (
            <div
              key={u.id}
              className="p-5 rounded-2xl bg-surface border border-border shadow-card space-y-4 hover:border-primary/40 transition-colors"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-10 h-10 rounded-xl bg-surface-alt border border-border flex items-center justify-center text-primary font-bold font-mono shrink-0 shadow-xs">
                    {u.role === 'admin' ? (
                      <Shield className="w-5 h-5 text-primary" />
                    ) : u.role === 'institution' ? (
                      <Building2 className="w-5 h-5 text-success" />
                    ) : (
                      <UserCheck className="w-5 h-5 text-secondary" />
                    )}
                  </div>
                  <div className="min-w-0">
                    <h3 className="font-bold text-sm text-text truncate">{u.full_name}</h3>
                    <div className="flex items-center gap-1.5 mt-0.5 text-xs text-muted font-mono">
                      <span>{u.email}</span>
                      <button
                        type="button"
                        onClick={() => handleCopyEmail(u.email)}
                        className="p-0.5 hover:text-text"
                        title="Copy email"
                      >
                        {isCopied ? <Check className="w-3 h-3 text-success" /> : <Copy className="w-3 h-3" />}
                      </button>
                    </div>
                  </div>
                </div>

                <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold uppercase border shrink-0 ${roleBadgeColor}`}>
                  {u.role_label}
                </span>
              </div>

              <div className="pt-3 border-t border-border/60 grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                <div>
                  <span className="text-[10px] font-mono text-muted uppercase block">Department / Bureau</span>
                  <span className="text-text font-medium text-[11px] truncate block">{u.department}</span>
                </div>
                <div>
                  <span className="text-[10px] font-mono text-muted uppercase block">Affiliation / Station</span>
                  <span className="text-text font-medium text-[11px] truncate block">
                    {u.institution_name || 'AICTE Headquarters'}
                  </span>
                </div>
              </div>

              <div className="flex items-center justify-between pt-2 border-t border-border/40 text-[10px] font-mono text-muted">
                <div className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-success" />
                  <span className="text-success font-semibold">Active Account</span>
                </div>
                {u.institution_id && (
                  <span className="text-primary font-bold">PID: {u.institution_id}</span>
                )}
                <span className="text-muted">ID: {u.id}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
