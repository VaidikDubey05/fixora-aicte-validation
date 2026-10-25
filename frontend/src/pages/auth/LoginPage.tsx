import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ShieldCheck,
  ArrowRight,
  UserCheck,
  Building2,
  Search,
  ShieldAlert,
  Loader2,
  AlertCircle,
} from 'lucide-react';
import { ThemeToggle } from '../../components/ThemeToggle';
import { useLogin } from '../../api/useLogin';
import { useAuth } from '../../context/AuthContext';
import { Role } from '../../lib/vocab';

interface DemoAccount {
  label: string;
  role: Role;
  email: string;
  pass: string;
  desc: string;
  icon: any;
}

const DEMO_ACCOUNTS: DemoAccount[] = [
  {
    label: 'Higher Education Institution',
    role: 'institution',
    email: 'principal@gecpune.edu.in',
    pass: 'Inst1@Fixora2026!',
    desc: 'Government College of Engineering, Pune',
    icon: Building2,
  },
  {
    label: 'Scrutiny Officer',
    role: 'scrutiny_officer',
    email: 'scrutiny@aicte.gov.in',
    pass: 'Scrutiny@Fixora2026!',
    desc: 'AICTE Intake Compliance & Dossier Review',
    icon: Search,
  },
  {
    label: 'Verification Bureau Officer',
    role: 'verification_officer',
    email: 'verification@aicte.gov.in',
    pass: 'Verification@Fixora2026!',
    desc: 'State & Central Registry Cross-Checks',
    icon: ShieldCheck,
  },
  {
    label: 'System Administrator',
    role: 'admin',
    email: 'admin@aicte.gov.in',
    pass: 'Admin@Fixora2026!',
    desc: 'Rule Packs Governance & Audit Chain',
    icon: ShieldAlert,
  },
];

export default function LoginPage() {
  const navigate = useNavigate();
  const { login: setAuthSession } = useAuth();
  const loginMutation = useLogin();

  const [username, setUsername] = useState('scrutiny@aicte.gov.in');
  const [password, setPassword] = useState('Scrutiny@Fixora2026!');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const fillDemoCredentials = (account: DemoAccount) => {
    setUsername(account.email);
    setPassword(account.pass);
    setErrorMessage(null);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    loginMutation.mutate(
      { username, password },
      {
        onSuccess: (res) => {
          setAuthSession(res.access_token, res.user);

          // Role-based redirect as required in STEP 3
          const role = res.user.role as Role;
          if (role === 'institution') {
            navigate('/institution/dashboard');
          } else if (role === 'verification_officer') {
            navigate('/officer/verification');
          } else if (role === 'admin') {
            navigate('/admin/analytics');
          } else {
            // scrutiny_officer
            navigate('/officer/overview');
          }
        },
        onError: (err: any) => {
          setErrorMessage(err.message || 'Invalid statutory credentials. Please verify your email and passcode.');
        },
      }
    );
  };

  return (
    <div className="min-h-screen bg-bg flex flex-col justify-center items-center p-4 sm:p-6 relative">
      <div className="absolute top-6 right-6">
        <ThemeToggle />
      </div>

      <div className="w-full max-w-xl space-y-6">
        {/* Main Card */}
        <div className="bg-surface border border-border rounded-card p-6 sm:p-8 shadow-modal space-y-6">
          {/* Emblem & Branding */}
          <div className="text-center space-y-2">
            <div className="w-14 h-14 rounded-2xl bg-hero-gradient mx-auto flex items-center justify-center text-white shadow-glow">
              <ShieldCheck className="w-8 h-8" />
            </div>
            <h1 className="text-2xl font-bold font-heading text-text tracking-tight">
              FIXORA PORTAL
            </h1>
            <p className="text-xs text-muted font-sans max-w-sm mx-auto">
              Statutory AI-Assisted Document Scrutiny & Verification Platform for AICTE Extension of Approval (EoA)
            </p>
          </div>

          {/* Advisory Decision Support Note */}
          <div className="p-3 rounded-xl bg-primary/10 border border-primary/20 text-xs text-text flex items-center gap-2">
            <UserCheck className="w-4 h-4 text-primary flex-shrink-0" />
            <span className="text-[11px] font-sans">
              <strong>Decision Support Only:</strong> Authorised statutory officers maintain sole adjudication authority.
            </span>
          </div>

          {/* Error Message if any */}
          {errorMessage && (
            <div className="p-3.5 rounded-xl bg-danger/10 border border-danger/30 text-xs text-danger flex items-center gap-2 font-medium">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{errorMessage}</span>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-mono text-muted mb-1 uppercase font-semibold">
                Official Email / PID
              </label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="officer@aicte.gov.in"
                className="w-full px-3.5 py-2.5 rounded-xl text-xs bg-surface border border-border text-text font-sans focus:border-primary focus:ring-2 focus:ring-primary/20 outline-none"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-mono text-muted mb-1 uppercase font-semibold">
                Security Credential / e-Passcode
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl text-xs bg-surface border border-border text-text font-sans focus:border-primary focus:ring-2 focus:ring-primary/20 outline-none"
                required
              />
            </div>

            <button
              type="submit"
              disabled={loginMutation.isPending}
              className="w-full py-3 rounded-xl font-heading font-bold text-xs bg-hero-gradient text-white shadow-glow hover:brightness-105 active:scale-95 transition-all flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {loginMutation.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Authenticating Session...</span>
                </>
              ) : (
                <>
                  <span>Authenticate Session</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>

          {/* Demo Access Cards Section */}
          <div className="pt-4 border-t border-border space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-mono uppercase font-bold text-muted tracking-wider">
                Instant Demo Access (Seeded Credentials)
              </span>
              <span className="text-[10px] text-primary font-mono font-semibold">Click to autofill</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              {DEMO_ACCOUNTS.map((acc) => {
                const Icon = acc.icon;
                const isSelected = username === acc.email;
                return (
                  <button
                    key={acc.role}
                    type="button"
                    onClick={() => fillDemoCredentials(acc)}
                    className={`p-3 rounded-xl border text-left transition-all flex items-start gap-2.5 ${
                      isSelected
                        ? 'bg-primary/10 border-primary ring-1 ring-primary/30 shadow-xs'
                        : 'bg-surface-alt/60 border-border hover:bg-surface-alt hover:border-primary/40'
                    }`}
                  >
                    <div className="p-1.5 rounded-lg bg-surface border border-border text-primary flex-shrink-0">
                      <Icon className="w-4 h-4" />
                    </div>
                    <div className="min-w-0">
                      <p className="text-xs font-bold font-heading text-text truncate">
                        {acc.label}
                      </p>
                      <p className="text-[10px] text-muted truncate mt-0.5">{acc.email}</p>
                      <span className="text-[9px] font-mono text-muted/70 block mt-1">
                        PW: {acc.pass}
                      </span>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          <div className="pt-2 text-center text-[10px] text-muted font-mono">
            <span>AICTE APH 2026-27 Compliant • Session Cryptographically Audited</span>
          </div>
        </div>
      </div>
    </div>
  );
}
