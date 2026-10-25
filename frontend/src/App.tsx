import React, { Suspense, lazy } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider } from './context/ThemeContext';
import { AuthProvider } from './context/AuthContext';
import { RequireRole } from './components/RequireRole';
import { AppShell } from './components/AppShell';
import { Skeleton } from './components/Skeleton';

// Lazy loaded page components
const LandingPage = lazy(() => import('./pages/LandingPage'));
const LoginPage = lazy(() => import('./pages/auth/LoginPage'));

// Institution Portal Routes
const InstitutionDashboardPage = lazy(() => import('./pages/institution/InstitutionDashboardPage'));
const SubmissionWizardPage = lazy(() => import('./pages/institution/SubmissionWizardPage'));
const ApplicationDetailPage = lazy(() => import('./pages/institution/ApplicationDetailPage'));

// Officer Scrutiny & Verification Bureau Routes
const OfficerOverviewPage = lazy(() => import('./pages/officer/OfficerOverviewPage'));
const ApplicationsQueuePage = lazy(() => import('./pages/officer/ApplicationsQueuePage'));
const ReviewWorkspacePage = lazy(() => import('./pages/officer/ReviewWorkspacePage'));
const VerificationBureauPage = lazy(() => import('./pages/officer/VerificationBureauPage'));
const InspectionQueuePage = lazy(() => import('./pages/officer/InspectionQueuePage'));

// Admin & Governance Routes
const AnalyticsPage = lazy(() => import('./pages/admin/AnalyticsPage'));
const RulePacksPage = lazy(() => import('./pages/admin/RulePacksPage'));
const RuleEditorPage = lazy(() => import('./pages/admin/RuleEditorPage'));
const AuditExplorerPage = lazy(() => import('./pages/admin/AuditExplorerPage'));
const UsersPage = lazy(() => import('./pages/admin/UsersPage'));

// Fallback 404 Route
const NotFoundPage = lazy(() => import('./pages/NotFoundPage'));

// Loading Fallback Component
const RouteLoadingFallback: React.FC = () => (
  <div className="space-y-4 p-6 max-w-5xl mx-auto">
    <div className="flex items-center justify-between pb-4">
      <Skeleton width={240} height={28} />
      <Skeleton width={120} height={36} />
    </div>
    <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
      <Skeleton variant="card" />
      <Skeleton variant="card" />
      <Skeleton variant="card" />
      <Skeleton variant="card" />
    </div>
    <Skeleton height={320} />
  </div>
);

export default function App() {
  return (
    <ThemeProvider>
      <BrowserRouter>
        <AuthProvider>
          <Suspense fallback={<RouteLoadingFallback />}>
            <Routes>
              {/* Public Landing & Auth Routes */}
              <Route path="/" element={<LandingPage />} />
              <Route path="/landing" element={<LandingPage />} />
              <Route path="/login" element={<LoginPage />} />

              {/* Authenticated Workspace wrapped in AppShell */}
              <Route element={<AppShell />}>
                {/* Institution Portal */}
                <Route path="institution">
                  <Route index element={<Navigate to="/institution/dashboard" replace />} />
                  <Route
                    path="dashboard"
                    element={
                      <RequireRole allowedRoles={['institution', 'admin']}>
                        <InstitutionDashboardPage />
                      </RequireRole>
                    }
                  />
                  <Route
                    path="submit"
                    element={
                      <RequireRole allowedRoles={['institution', 'admin']}>
                        <SubmissionWizardPage />
                      </RequireRole>
                    }
                  />
                  <Route
                    path="applications/new"
                    element={
                      <RequireRole allowedRoles={['institution', 'admin']}>
                        <SubmissionWizardPage />
                      </RequireRole>
                    }
                  />
                  <Route
                    path="applications/:id"
                    element={
                      <RequireRole allowedRoles={['institution', 'admin']}>
                        <ApplicationDetailPage />
                      </RequireRole>
                    }
                  />
                </Route>

                {/* Officer Scrutiny & Verification */}
                <Route path="officer">
                  <Route index element={<Navigate to="/officer/overview" replace />} />
                  <Route
                    path="overview"
                    element={
                      <RequireRole allowedRoles={['scrutiny_officer', 'verification_officer', 'admin']}>
                        <OfficerOverviewPage />
                      </RequireRole>
                    }
                  />
                  <Route
                    path="queue"
                    element={
                      <RequireRole allowedRoles={['scrutiny_officer', 'verification_officer', 'admin']}>
                        <ApplicationsQueuePage />
                      </RequireRole>
                    }
                  />
                  <Route
                    path="applications"
                    element={
                      <RequireRole allowedRoles={['scrutiny_officer', 'verification_officer', 'admin']}>
                        <ApplicationsQueuePage />
                      </RequireRole>
                    }
                  />
                  <Route
                    path="applications/:id"
                    element={
                      <RequireRole allowedRoles={['scrutiny_officer', 'verification_officer', 'admin']}>
                        <ReviewWorkspacePage />
                      </RequireRole>
                    }
                  />
                  <Route
                    path="review/:id"
                    element={
                      <RequireRole allowedRoles={['scrutiny_officer', 'verification_officer', 'admin']}>
                        <ReviewWorkspacePage />
                      </RequireRole>
                    }
                  />
                  <Route
                    path="verification"
                    element={
                      <RequireRole allowedRoles={['verification_officer', 'scrutiny_officer', 'admin']}>
                        <VerificationBureauPage />
                      </RequireRole>
                    }
                  />
                  <Route
                    path="inspection"
                    element={
                      <RequireRole allowedRoles={['scrutiny_officer', 'verification_officer', 'admin']}>
                        <InspectionQueuePage />
                      </RequireRole>
                    }
                  />
                  <Route
                    path="audit"
                    element={
                      <RequireRole allowedRoles={['scrutiny_officer', 'verification_officer', 'admin']}>
                        <AuditExplorerPage />
                      </RequireRole>
                    }
                  />
                </Route>

                {/* Statutory Admin & Model Governance */}
                <Route path="admin">
                  <Route index element={<Navigate to="/admin/analytics" replace />} />
                  <Route
                    path="analytics"
                    element={
                      <RequireRole allowedRoles={['admin']}>
                        <AnalyticsPage />
                      </RequireRole>
                    }
                  />
                  <Route
                    path="rules"
                    element={
                      <RequireRole allowedRoles={['admin']}>
                        <RulePacksPage />
                      </RequireRole>
                    }
                  />
                  <Route
                    path="rules/:id"
                    element={
                      <RequireRole allowedRoles={['admin']}>
                        <RuleEditorPage />
                      </RequireRole>
                    }
                  />
                  <Route
                    path="rules/editor"
                    element={
                      <RequireRole allowedRoles={['admin']}>
                        <RuleEditorPage />
                      </RequireRole>
                    }
                  />
                  <Route
                    path="audit"
                    element={
                      <RequireRole allowedRoles={['admin']}>
                        <AuditExplorerPage />
                      </RequireRole>
                    }
                  />
                  <Route
                    path="users"
                    element={
                      <RequireRole allowedRoles={['admin']}>
                        <UsersPage />
                      </RequireRole>
                    }
                  />
                </Route>

                {/* Catch-all Not Found Route */}
                <Route path="*" element={<NotFoundPage />} />
              </Route>
            </Routes>
          </Suspense>
        </AuthProvider>
      </BrowserRouter>
    </ThemeProvider>
  );
}
