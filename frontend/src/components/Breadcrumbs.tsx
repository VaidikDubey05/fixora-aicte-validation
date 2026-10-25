import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { ChevronRight, Home } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

interface BreadcrumbItem {
  label: string;
  to?: string;
}

export const Breadcrumbs: React.FC<{ items?: BreadcrumbItem[]; className?: string }> = ({
  items,
  className = '',
}) => {
  const location = useLocation();
  const { role } = useAuth();

  // If items not explicitly provided, generate automatically from pathname
  const generateBreadcrumbs = (): BreadcrumbItem[] => {
    const segments = location.pathname.split('/').filter(Boolean);
    const breadcrumbs: BreadcrumbItem[] = [];

    // Root home based on role
    let homeUrl = '/login';
    let homeLabel = 'Home';
    if (role === 'institution') {
      homeUrl = '/institution/dashboard';
      homeLabel = 'Institution Portal';
    } else if (role === 'scrutiny_officer') {
      homeUrl = '/officer/overview';
      homeLabel = 'Scrutiny Overview';
    } else if (role === 'verification_officer') {
      homeUrl = '/officer/verification';
      homeLabel = 'Verification Bureau';
    } else if (role === 'admin') {
      homeUrl = '/admin/analytics';
      homeLabel = 'Administration';
    }

    breadcrumbs.push({ label: homeLabel, to: homeUrl });

    let currentPath = '';
    for (let i = 0; i < segments.length; i++) {
      const seg = segments[i];
      currentPath += `/${seg}`;

      // Skip root role segments since home already points there
      if (['institution', 'officer', 'admin'].includes(seg) && i === 0) continue;

      let label = seg;
      if (seg === 'applications') label = 'Applications';
      else if (seg === 'overview') label = 'Overview';
      else if (seg === 'dashboard') label = 'Dashboard';
      else if (seg === 'verification') label = 'Registry Verification';
      else if (seg === 'inspection') label = 'On-site Inspection';
      else if (seg === 'audit') label = 'Audit Ledger';
      else if (seg === 'rules') label = 'Rule Packs';
      else if (seg === 'analytics') label = 'Statutory Analytics';
      else if (seg === 'users') label = 'Statutory Users';
      else if (seg === 'new') label = 'New Dossier';
      else if (seg.startsWith('APP-') || seg.startsWith('DOC-') || seg.startsWith('RULE-')) {
        label = seg;
      }

      breadcrumbs.push({
        label,
        to: i === segments.length - 1 ? undefined : currentPath,
      });
    }

    return breadcrumbs;
  };

  const trail = items || generateBreadcrumbs();

  if (trail.length <= 1) return null;

  return (
    <nav aria-label="Breadcrumb" className={`flex items-center gap-1.5 text-xs text-muted font-sans py-2 ${className}`}>
      <Home className="w-3.5 h-3.5 text-muted flex-shrink-0" />
      {trail.map((item, idx) => {
        const isLast = idx === trail.length - 1;
        return (
          <React.Fragment key={idx}>
            {idx > 0 && <ChevronRight className="w-3 h-3 text-border flex-shrink-0" />}
            {item.to && !isLast ? (
              <Link
                to={item.to}
                className="hover:text-primary transition-colors truncate max-w-[160px] font-medium"
              >
                {item.label}
              </Link>
            ) : (
              <span className={`truncate max-w-[200px] ${isLast ? 'text-text font-semibold' : ''}`}>
                {item.label}
              </span>
            )}
          </React.Fragment>
        );
      })}
    </nav>
  );
};
