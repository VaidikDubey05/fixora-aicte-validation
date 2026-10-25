import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Role } from '../lib/vocab';
import { Skeleton } from './Skeleton';

interface RequireRoleProps {
  allowedRoles?: Role[];
  children: React.ReactNode;
}

export const RequireRole: React.FC<RequireRoleProps> = ({ allowedRoles, children }) => {
  const { user, role, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="p-8 space-y-4 max-w-4xl mx-auto">
        <Skeleton height={32} width={280} />
        <Skeleton height={200} />
      </div>
    );
  }

  // Not authenticated
  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Role not allowed: redirect to role default page
  if (allowedRoles && allowedRoles.length > 0 && role && !allowedRoles.includes(role)) {
    const roleHomeMap: Record<Role, string> = {
      institution: '/institution/dashboard',
      scrutiny_officer: '/officer/overview',
      verification_officer: '/officer/verification',
      admin: '/admin/analytics',
    };
    return <Navigate to={roleHomeMap[role] || '/login'} replace />;
  }

  return <>{children}</>;
};
