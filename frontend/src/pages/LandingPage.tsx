import { useNavigate } from 'react-router-dom';
import {
  ShieldCheck,
  ArrowRight,
  Sparkles,
  Building2,
  Search,
  CheckCircle2,
  ShieldAlert,
  FileText,
  Lock,
  Layers,
  BarChart3,
  GitCommit,
  ChevronRight,
  LogIn,
} from 'lucide-react';
import { ThemeToggle } from '../components/ThemeToggle';
import { Hero3DVisualizer } from '../components/landing/Hero3DVisualizer';
import { InteractivePipeline3D } from '../components/landing/InteractivePipeline3D';
import { useAuth } from '../context/AuthContext';
import { Role } from '../lib/vocab';
import { DEMO_USERS } from '../lib/mockFallback';

export default function LandingPage() {
  const navigate = useNavigate();
  const { role, login: setAuthSession } = useAuth();

  const handleLaunchRole = (targetRole: Role, email: string) => {
    const user = DEMO_USERS[email];
    if (user) {
      setAuthSession(`mock_jwt_token_${targetRole}`, user);
      if (targetRole === 'institution') navigate('/institution/dashboard');
      else if (targetRole === 'verification_officer') navigate('/officer/verification');
      else if (targetRole === 'admin') navigate('/admin/analytics');
      else navigate('/officer/overview');
    } else {
      navigate('/login');
    }
  };

  return (
    <div className="min-h-screen bg-bg text-text font-sans selection:bg-primary/20 selection:text-primary">
      {/* Top Floating Glass Navigation Header */}
      <header className="sticky top-0 z-40 bg-surface/80 backdrop-blur-md border-b border-border transition-colors">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-4">
          {/* Logo & Emblem */}
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-hero-gradient flex items-center justify-center text-white shadow-glow">
              <ShieldCheck className="w-5 h-5 stroke-[2.5]" />
            </div>
            <div className="flex flex-col">
              <div className="flex items-center gap-2">
                <span className="font-heading font-extrabold text-lg tracking-tight text-text">
                  FIXORA
                </span>
                <span className="hidden sm:inline-block px-1.5 py-0.2 rounded text-[10px] font-mono font-bold bg-primary/10 text-primary border border-primary/20">
                  AICTE EoA 2026-27
                </span>
              </div>
              <span className="text-[10px] text-muted hidden md:inline font-sans">
                Statutory AI Scrutiny & Verification Platform
              </span>
            </div>
          </div>

          {/* Quick Nav Anchor Links */}
          <nav className="hidden lg:flex items-center gap-6 text-xs font-medium text-muted">
            <a href="#pipeline" className="hover:text-text transition-colors">
              7-Stage Pipeline
            </a>
            <a href="#features" className="hover:text-text transition-colors">
              Core Capabilities
            </a>
            <a href="#personas" className="hover:text-text transition-colors">
              Statutory Personas
            </a>
            <a href="#metrics" className="hover:text-text transition-colors">
              Benchmark Metrics
            </a>
          </nav>

          {/* Controls & Portal CTA */}
          <div className="flex items-center gap-3">
            <ThemeToggle />

            {role ? (
              <button
                type="button"
                onClick={() => navigate('/officer/overview')}
                className="px-4 py-2 rounded-xl text-xs font-bold font-heading bg-hero-gradient text-white shadow-glow hover:brightness-105 active:scale-95 transition-all flex items-center gap-1.5"
              >
                <span>Go to Workspace</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            ) : (
              <button
                type="button"
                onClick={() => navigate('/login')}
                className="px-4 py-2 rounded-xl text-xs font-bold font-heading bg-hero-gradient text-white shadow-glow hover:brightness-105 active:scale-95 transition-all flex items-center gap-1.5"
              >
                <span>Enter Portal</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Main Hero Section */}
      <section className="relative pt-10 sm:pt-16 pb-16 px-4 sm:px-6 overflow-hidden">
        {/* Background Ambient Lighting Blobs */}
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[350px] bg-gradient-to-r from-primary/15 via-secondary/15 to-transparent blur-3xl rounded-full pointer-events-none" />

        <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
          {/* Left Column: Headline, Description & CTAs */}
          <div className="lg:col-span-7 space-y-6 text-center lg:text-left">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-primary/10 border border-primary/25 text-xs font-sans font-semibold text-primary">
              <Sparkles className="w-3.5 h-3.5 text-secondary animate-spin-slow" />
              <span>National Statutory Scrutiny Platform</span>
              <span className="w-1 h-1 rounded-full bg-primary" />
              <span className="text-muted font-normal">AICTE EoA 2026-27</span>
            </div>

            <h1 className="text-3xl sm:text-5xl lg:text-6xl font-extrabold font-heading text-text tracking-tight leading-[1.12]">
              Autonomous AI Scrutiny for{' '}
              <span className="bg-gradient-to-r from-primary via-secondary to-accent bg-clip-text text-transparent">
                Technical Education
              </span>{' '}
              Approvals.
            </h1>

            <p className="text-sm sm:text-base text-muted font-sans max-w-2xl mx-auto lg:mx-0 leading-relaxed">
              Accelerating Extension of Approval (EoA) decisions from 28 days down to 3.4 days. FIXORA delivers high-precision OCR extraction, automated APH 2026-27 handbook rule compliance checking, cross-document reconciliation, and an immutable SHA-256 cryptographic audit trail.
            </p>

            {/* Primary Action Buttons */}
            <div className="flex flex-col sm:flex-row items-center justify-center lg:justify-start gap-3 pt-2">
              <button
                type="button"
                onClick={() => navigate('/login')}
                className="w-full sm:w-auto px-6 py-3.5 rounded-xl font-heading font-bold text-sm bg-hero-gradient text-white shadow-glow hover:brightness-105 active:scale-95 transition-all flex items-center justify-center gap-2"
              >
                <LogIn className="w-4 h-4" />
                <span>Log In to Portal</span>
                <ArrowRight className="w-4 h-4" />
              </button>

              <a
                href="#pipeline"
                className="w-full sm:w-auto px-5 py-3.5 rounded-xl font-heading font-semibold text-sm bg-surface-alt border border-border hover:bg-surface text-text hover:border-primary/40 transition-all flex items-center justify-center gap-2"
              >
                <Layers className="w-4 h-4 text-primary" />
                <span>Explore 7-Stage Pipeline</span>
              </a>
            </div>

            {/* Statutory Decision Support Callout */}
            <div className="p-3.5 rounded-2xl bg-surface border border-border max-w-lg mx-auto lg:mx-0 flex items-start gap-3 text-xs text-muted shadow-xs">
              <div className="p-1 rounded-md bg-primary/10 text-primary shrink-0 mt-0.5">
                <ShieldCheck className="w-3.5 h-3.5" />
              </div>
              <p className="leading-snug">
                <strong className="text-text font-semibold">Statutory Adjudication Protocol:</strong> All automated findings serve as decision support only. AICTE Scrutiny Officers retain sole statutory determination authority.
              </p>
            </div>
          </div>

          {/* Right Column: Interactive 3D Document Scanner Deck */}
          <div className="lg:col-span-5 flex justify-center">
            <Hero3DVisualizer />
          </div>
        </div>
      </section>

      {/* Live Benchmark KPI Metrics Bar */}
      <section id="metrics" className="py-10 border-y border-border bg-surface-alt/40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 grid grid-cols-2 lg:grid-cols-4 gap-6">
          <div className="p-4 rounded-2xl bg-surface border border-border shadow-xs text-center space-y-1">
            <div className="text-2xl sm:text-3xl font-extrabold font-mono text-primary">
              100.0%
            </div>
            <div className="text-xs font-bold font-heading text-text">Extraction Accuracy</div>
            <p className="text-[10px] text-muted font-sans">Evaluated across 359 statutory documents</p>
          </div>

          <div className="p-4 rounded-2xl bg-surface border border-border shadow-xs text-center space-y-1">
            <div className="text-2xl sm:text-3xl font-extrabold font-mono text-secondary">
              3.4 Days
            </div>
            <div className="text-xs font-bold font-heading text-text">Average Scrutiny Turnaround</div>
            <p className="text-[10px] text-muted font-sans">Reduced from 28 days manual cycle</p>
          </div>

          <div className="p-4 rounded-2xl bg-surface border border-border shadow-xs text-center space-y-1">
            <div className="text-2xl sm:text-3xl font-extrabold font-mono text-accent">
              35+ Rules
            </div>
            <div className="text-xs font-bold font-heading text-text">APH 2026-27 Rule Packs</div>
            <p className="text-[10px] text-muted font-sans">Land, built-up areas, fire NOC & TER</p>
          </div>

          <div className="p-4 rounded-2xl bg-surface border border-border shadow-xs text-center space-y-1">
            <div className="text-2xl sm:text-3xl font-extrabold font-mono text-success">
              SHA-256
            </div>
            <div className="text-xs font-bold font-heading text-text">Cryptographic Audit Chain</div>
            <p className="text-[10px] text-muted font-sans">Immutable tamper-evident ledger</p>
          </div>
        </div>
      </section>

      {/* Interactive 7-Stage Autonomous Pipeline Section */}
      <section id="pipeline" className="py-20 px-4 sm:px-6">
        <div className="max-w-7xl mx-auto space-y-12">
          <div className="text-center max-w-3xl mx-auto space-y-3">
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-primary bg-primary/10 px-3 py-1 rounded-full border border-primary/20">
              End-to-End Autonomous Workflow
            </span>
            <h2 className="text-2xl sm:text-4xl font-extrabold font-heading text-text tracking-tight">
              The 7-Stage Autonomous Scrutiny Architecture
            </h2>
            <p className="text-xs sm:text-sm text-muted font-sans leading-relaxed">
              Explore how each statutory annexure flows from quarantine intake through OCR coordinate extraction, handbook threshold rules, cross-document reconciliation, and external registry gateways.
            </p>
          </div>

          <InteractivePipeline3D />
        </div>
      </section>

      {/* Core Platform Capabilities */}
      <section id="features" className="py-16 px-4 sm:px-6 bg-surface-alt/30 border-t border-border">
        <div className="max-w-7xl mx-auto space-y-12">
          <div className="text-center max-w-2xl mx-auto space-y-2">
            <h2 className="text-2xl sm:text-3xl font-bold font-heading text-text">
              Engineered for Statutory Rigor
            </h2>
            <p className="text-xs text-muted font-sans">
              Designed specifically to meet the high security and transparency demands of the AICTE Approval Bureau.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {/* Feature 1 */}
            <div className="p-6 rounded-2xl bg-surface border border-border shadow-card space-y-3">
              <div className="w-10 h-10 rounded-xl bg-primary/10 text-primary flex items-center justify-center">
                <FileText className="w-5 h-5" />
              </div>
              <h3 className="text-base font-bold font-heading text-text">
                Three-Pane Review Workspace
              </h3>
              <p className="text-xs text-muted font-sans leading-relaxed">
                Ties findings, high-resolution document canvas, and decision panel together. Features bounding box pulsing, 90° rotation for architectural drawings, and keyboard hotkeys (J/K/C/D).
              </p>
            </div>

            {/* Feature 2 */}
            <div className="p-6 rounded-2xl bg-surface border border-border shadow-card space-y-3">
              <div className="w-10 h-10 rounded-xl bg-secondary/10 text-secondary flex items-center justify-center">
                <Lock className="w-5 h-5" />
              </div>
              <h3 className="text-base font-bold font-heading text-text">
                Dual-Authorization Maker-Checker
              </h3>
              <p className="text-xs text-muted font-sans leading-relaxed">
                Rule packs require dual authorization: the author submits modifications in CodeMirror YAML editor, but a separate independent administrator must review and approve before publishing.
              </p>
            </div>

            {/* Feature 3 */}
            <div className="p-6 rounded-2xl bg-surface border border-border shadow-card space-y-3">
              <div className="w-10 h-10 rounded-xl bg-accent/10 text-accent flex items-center justify-center">
                <GitCommit className="w-5 h-5" />
              </div>
              <h3 className="text-base font-bold font-heading text-text">
                Immutable SHA-256 Audit Ledger
              </h3>
              <p className="text-xs text-muted font-sans leading-relaxed">
                Every uploaded annexure, OCR parse, officer adjudication, and registry query is chained to the previous block via SHA-256 hashing. One-click integrity verification detects any broken sequence.
              </p>
            </div>

            {/* Feature 4 */}
            <div className="p-6 rounded-2xl bg-surface border border-border shadow-card space-y-3">
              <div className="w-10 h-10 rounded-xl bg-success/10 text-success flex items-center justify-center">
                <Sparkles className="w-5 h-5" />
              </div>
              <h3 className="text-base font-bold font-heading text-text">
                Ask FIXORA Handbook Copilot
              </h3>
              <p className="text-xs text-muted font-sans leading-relaxed">
                Trained on the AICTE Approval Process Handbook (APH 2026-27). Answers statutory inquiries with verbatim chapter and clause citations, automatic application context detection, and typing indicators.
              </p>
            </div>

            {/* Feature 5 */}
            <div className="p-6 rounded-2xl bg-surface border border-border shadow-card space-y-3">
              <div className="w-10 h-10 rounded-xl bg-primary/10 text-primary flex items-center justify-center">
                <ShieldCheck className="w-5 h-5" />
              </div>
              <h3 className="text-base font-bold font-heading text-text">
                Mandatory Written Reason Protocol
              </h3>
              <p className="text-xs text-muted font-sans leading-relaxed">
                Adjudicating officers cannot confirm or dismiss AI findings without entering a written reason of at least 10 characters, ensuring defensibility and accountability in regulatory decisions.
              </p>
            </div>

            {/* Feature 6 */}
            <div className="p-6 rounded-2xl bg-surface border border-border shadow-card space-y-3">
              <div className="w-10 h-10 rounded-xl bg-secondary/10 text-secondary flex items-center justify-center">
                <BarChart3 className="w-5 h-5" />
              </div>
              <h3 className="text-base font-bold font-heading text-text">
                Synthetic Benchmark Analytics
              </h3>
              <p className="text-xs text-muted font-sans leading-relaxed">
                Directly grounded in empirical evaluations with precision, recall, and false positive metrics displayed transparently across anomaly, duplicate, and mismatch defect types.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Statutory Personas Quick Launchpad */}
      <section id="personas" className="py-20 px-4 sm:px-6">
        <div className="max-w-7xl mx-auto space-y-12">
          <div className="text-center max-w-2xl mx-auto space-y-2">
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-primary bg-primary/10 px-3 py-1 rounded-full border border-primary/20">
              Statutory Roles & Access
            </span>
            <h2 className="text-2xl sm:text-4xl font-extrabold font-heading text-text tracking-tight">
              Access by Statutory Authority
            </h2>
            <p className="text-xs sm:text-sm text-muted font-sans">
              Sign in directly to your authorized statutory workspace or scrutiny bureau.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {/* Persona 1: Institution */}
            <div className="p-6 rounded-3xl bg-surface border border-border shadow-card flex flex-col justify-between space-y-4 hover:border-primary/40 transition-colors">
              <div className="space-y-3">
                <div className="w-10 h-10 rounded-xl bg-primary/10 text-primary flex items-center justify-center">
                  <Building2 className="w-5 h-5" />
                </div>
                <div>
                  <span className="text-[10px] font-mono text-muted uppercase font-bold">APPLICANT</span>
                  <h4 className="text-base font-bold font-heading text-text">Higher Education Institution</h4>
                </div>
                <p className="text-xs text-muted font-sans">
                  Dr. Suresh Patil (Principal, GEC Pune). 4-step wizard, document replacement & live pipeline status.
                </p>
              </div>
              <button
                type="button"
                onClick={() => handleLaunchRole('institution', 'principal@gecpune.edu.in')}
                className="w-full py-2.5 rounded-xl text-xs font-bold font-heading bg-surface-alt hover:bg-primary hover:text-white border border-border transition-colors flex items-center justify-center gap-1.5"
              >
                <span>Launch Institution Portal</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>

            {/* Persona 2: Scrutiny Officer */}
            <div className="p-6 rounded-3xl bg-surface border border-border shadow-card flex flex-col justify-between space-y-4 hover:border-primary/40 transition-colors ring-2 ring-primary/20">
              <div className="space-y-3">
                <div className="w-10 h-10 rounded-xl bg-primary text-white flex items-center justify-center shadow-glow">
                  <Search className="w-5 h-5" />
                </div>
                <div>
                  <span className="text-[10px] font-mono text-primary uppercase font-bold">RECOMMENDED</span>
                  <h4 className="text-base font-bold font-heading text-text">Scrutiny Officer</h4>
                </div>
                <p className="text-xs text-muted font-sans">
                  S. Ramanathan. Three-pane review workspace, bounding box inspection, and J/K/C/D keyboard shortcuts.
                </p>
              </div>
              <button
                type="button"
                onClick={() => handleLaunchRole('scrutiny_officer', 'scrutiny@aicte.gov.in')}
                className="w-full py-2.5 rounded-xl text-xs font-bold font-heading bg-hero-gradient text-white shadow-glow hover:brightness-105 transition-all flex items-center justify-center gap-1.5"
              >
                <span>Launch Scrutiny Review</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>

            {/* Persona 3: Verification Officer */}
            <div className="p-6 rounded-3xl bg-surface border border-border shadow-card flex flex-col justify-between space-y-4 hover:border-primary/40 transition-colors">
              <div className="space-y-3">
                <div className="w-10 h-10 rounded-xl bg-secondary/15 text-secondary flex items-center justify-center">
                  <CheckCircle2 className="w-5 h-5" />
                </div>
                <div>
                  <span className="text-[10px] font-mono text-muted uppercase font-bold">REGISTRY</span>
                  <h4 className="text-base font-bold font-heading text-text">Verification Bureau</h4>
                </div>
                <p className="text-xs text-muted font-sans">
                  Ananya Sharma. State IGR land title registry, municipal NOCs, and manual confirmation upload form.
                </p>
              </div>
              <button
                type="button"
                onClick={() => handleLaunchRole('verification_officer', 'verification@aicte.gov.in')}
                className="w-full py-2.5 rounded-xl text-xs font-bold font-heading bg-surface-alt hover:bg-secondary hover:text-white border border-border transition-colors flex items-center justify-center gap-1.5"
              >
                <span>Launch Bureau Queue</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>

            {/* Persona 4: System Admin */}
            <div className="p-6 rounded-3xl bg-surface border border-border shadow-card flex flex-col justify-between space-y-4 hover:border-primary/40 transition-colors">
              <div className="space-y-3">
                <div className="w-10 h-10 rounded-xl bg-accent/15 text-accent flex items-center justify-center">
                  <ShieldAlert className="w-5 h-5" />
                </div>
                <div>
                  <span className="text-[10px] font-mono text-muted uppercase font-bold">GOVERNANCE</span>
                  <h4 className="text-base font-bold font-heading text-text">System Administrator</h4>
                </div>
                <p className="text-xs text-muted font-sans">
                  AICTE Admin. CodeMirror YAML rule editor, maker-checker dual approval, and cryptographic audit explorer.
                </p>
              </div>
              <button
                type="button"
                onClick={() => handleLaunchRole('admin', 'admin@aicte.gov.in')}
                className="w-full py-2.5 rounded-xl text-xs font-bold font-heading bg-surface-alt hover:bg-accent hover:text-white border border-border transition-colors flex items-center justify-center gap-1.5"
              >
                <span>Launch Governance Deck</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border bg-surface py-12 px-4 sm:px-6">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-6 text-xs text-muted font-sans">
          <div className="flex items-center gap-3">
            <div className="w-7 h-7 rounded-lg bg-hero-gradient flex items-center justify-center text-white shadow-xs">
              <ShieldCheck className="w-4 h-4" />
            </div>
            <div>
              <span className="font-heading font-extrabold text-text">FIXORA PLATFORM</span>
              <span className="block text-[10px] text-muted">Smart India Hackathon 2026 • AICTE Approval Bureau</span>
            </div>
          </div>

          <div className="flex items-center gap-6 text-xs">
            <button
              type="button"
              onClick={() => navigate('/login')}
              className="hover:text-text transition-colors font-medium"
            >
              Statutory Login
            </button>
            <a href="#pipeline" className="hover:text-text transition-colors">
              Pipeline
            </a>
            <a href="#features" className="hover:text-text transition-colors">
              Capabilities
            </a>
          </div>

          <p className="text-[11px] text-muted font-mono">
            © 2026 AICTE EoA. Statutory Scrutiny & Verification Platform.
          </p>
        </div>
      </footer>
    </div>
  );
}
