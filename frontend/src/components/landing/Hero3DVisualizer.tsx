import React, { useState, useRef } from 'react';
import {
  ShieldCheck,
  CheckCircle2,
  Sparkles,
  Cpu,
  Eye,
  Check,
} from 'lucide-react';

export const Hero3DVisualizer: React.FC = () => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [rotateX, setRotateX] = useState<number>(12);
  const [rotateY, setRotateY] = useState<number>(-14);
  const [isHovered, setIsHovered] = useState<boolean>(false);

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const centerX = rect.width / 2;
    const centerY = rect.height / 2;

    // Calculate interactive tilt angles (-20 to +20 degrees)
    const rotX = -((y - centerY) / centerY) * 16;
    const rotY = ((x - centerX) / centerX) * 18;

    setRotateX(rotX);
    setRotateY(rotY);
  };

  const handleMouseLeave = () => {
    setIsHovered(false);
    // Return to gentle default perspective
    setRotateX(10);
    setRotateY(-12);
  };

  return (
    <div
      ref={containerRef}
      onMouseMove={handleMouseMove}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={handleMouseLeave}
      className="relative w-full max-w-[540px] h-[520px] mx-auto perspective-1200 cursor-grab active:cursor-grabbing select-none"
    >
      {/* Ambient Radial Glow Behind the 3D Stage */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[420px] h-[420px] bg-gradient-to-tr from-primary/30 via-secondary/25 to-accent/20 rounded-full blur-3xl pointer-events-none animate-pulse" />

      {/* 3D Transform Stage Container */}
      <div
        style={{
          transform: `rotateX(${rotateX}deg) rotateY(${rotateY}deg)`,
          transition: isHovered ? 'transform 0.1s ease-out' : 'transform 0.6s cubic-bezier(0.2, 0.8, 0.2, 1)',
        }}
        className="relative w-full h-full transform-style-3d flex items-center justify-center"
      >
        {/* Layer 0: Background Holographic Grid Plane */}
        <div
          style={{ transform: 'translateZ(-40px)' }}
          className="absolute inset-4 rounded-3xl border border-primary/20 bg-primary/5 backdrop-blur-xs opacity-70 pointer-events-none"
        >
          <div className="absolute inset-0 bg-[radial-gradient(#5B5BFF_1px,transparent_1px)] [background-size:16px_16px] opacity-25" />
        </div>

        {/* Layer 1: Base Statutory Document (Land Title & Architect Blueprint Mockup) */}
        <div
          style={{ transform: 'translateZ(0px)' }}
          className="relative w-[360px] sm:w-[390px] h-[460px] bg-white text-slate-900 rounded-2xl shadow-floating border border-slate-200/80 p-6 flex flex-col justify-between overflow-hidden"
        >
          {/* Animated Glowing Laser Scanline */}
          <div className="absolute left-0 right-0 h-1 bg-gradient-to-r from-transparent via-secondary to-transparent shadow-[0_0_15px_#00D1C1] animate-scanline z-20 pointer-events-none" />

          {/* Document Header & State Emblem */}
          <div className="border-b border-slate-200 pb-3 flex items-start justify-between">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center text-primary font-bold text-xs">
                GOI
              </div>
              <div>
                <p className="text-[9px] font-mono font-bold uppercase tracking-wider text-slate-400">
                  Statutory Regulatory Record
                </p>
                <h4 className="text-xs font-bold font-serif text-slate-900">
                  LAND TITLE & SURVEY DEED
                </h4>
              </div>
            </div>
            <span className="px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200 text-[9px] font-mono font-bold flex items-center gap-1">
              <Check className="w-2.5 h-2.5" /> CERTIFIED
            </span>
          </div>

          {/* Document Content Mockup with Bounding Box Highlights */}
          <div className="space-y-3 py-2 text-xs font-sans">
            <div className="flex justify-between items-center text-[10px] text-slate-500 font-mono">
              <span>Ref: MH/2026/LAND-0041</span>
              <span>Reg: Pune Central</span>
            </div>

            {/* Highlighted Bounding Box 1: Acreage */}
            <div className="relative p-2.5 rounded-lg border-2 border-primary bg-primary/10 transition-transform">
              <div className="absolute -top-3 left-2 px-1.5 py-0.5 rounded bg-primary text-white text-[8px] font-mono font-bold flex items-center gap-1 shadow-xs">
                <Sparkles className="w-2 h-2 text-secondary" />
                <span>EXTRACTED: land_area</span>
              </div>
              <p className="text-[11px] font-bold text-slate-800">
                Total Campus Land: <strong className="text-primary font-mono font-extrabold">42.50 Contiguous Acres</strong>
              </p>
              <p className="text-[9px] text-slate-500">
                Survey Nos: 142/1, 142/2, 143/A • Taluka: Haveli
              </p>
            </div>

            {/* Highlighted Bounding Box 2: Owner Institution */}
            <div className="relative p-2 rounded-lg border border-secondary/80 bg-secondary/10">
              <div className="text-[9px] font-mono text-slate-500">GRANTEE INSTITUTION</div>
              <div className="text-[11px] font-semibold text-slate-800">
                Government College of Engineering, Pune (COEP Tech)
              </div>
            </div>

            {/* Mock Signature & Stamp */}
            <div className="pt-2 flex items-center justify-between">
              <div className="w-16 h-16 rounded-full border-2 border-dashed border-primary/40 flex items-center justify-center p-1 text-center">
                <span className="text-[7px] font-mono font-bold text-primary/70 leading-tight">
                  DIGITAL NOTARY SEAL
                </span>
              </div>
              <div className="text-right">
                <div className="font-mono text-[9px] text-slate-400">DIGITALLY SIGNED</div>
                <div className="font-serif italic text-xs font-bold text-slate-700">Sub-Registrar Pune</div>
                <div className="text-[8px] font-mono text-emerald-600 font-bold">SHA-256 VALIDATED</div>
              </div>
            </div>
          </div>

          {/* Document Footer */}
          <div className="border-t border-slate-100 pt-2 flex items-center justify-between text-[8px] font-mono text-slate-400">
            <span>AICTE Approval Process Handbook (APH) 2026-27</span>
            <span>Page 1 of 4</span>
          </div>
        </div>

        {/* Layer 2: Floating 3D AI Adjudication Card */}
        <div
          style={{
            transform: 'translateZ(55px) translateX(45px) translateY(-35px)',
          }}
          className="absolute right-0 top-12 w-64 bg-surface/95 backdrop-blur-md border border-primary/30 rounded-2xl shadow-modal p-4 space-y-3 animate-float"
        >
          <div className="flex items-center justify-between border-b border-border/60 pb-2">
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded-lg bg-hero-gradient flex items-center justify-center text-white shadow-glow">
                <Cpu className="w-3.5 h-3.5" />
              </div>
              <div>
                <div className="text-[10px] font-mono font-bold text-primary">RULE-APH-AREA-03</div>
                <div className="text-[9px] text-muted font-sans">Land Contiguity Check</div>
              </div>
            </div>
            <span className="px-1.5 py-0.5 rounded-full bg-success/15 text-success border border-success/30 text-[9px] font-mono font-bold">
              PASSED
            </span>
          </div>

          <div className="space-y-1.5 text-[11px] font-sans">
            <div className="flex justify-between items-center text-muted text-[10px]">
              <span>Required: &gt;= 7.5 Acres</span>
              <span className="text-success font-bold font-mono">Confidence: 98.5%</span>
            </div>
            <div className="h-1.5 w-full bg-surface-alt rounded-full overflow-hidden">
              <div className="h-full bg-gradient-to-r from-secondary to-success rounded-full w-[98.5%]" />
            </div>
            <p className="text-[10px] text-text font-medium leading-tight pt-1">
              Cross-checked against architectural site layout blueprint with 0% boundary variance.
            </p>
          </div>
        </div>

        {/* Layer 3: Floating 3D Cryptographic Chain Integrity Token */}
        <div
          style={{
            transform: 'translateZ(75px) translateX(-60px) translateY(75px)',
          }}
          className="absolute left-2 bottom-12 w-60 bg-surface/95 backdrop-blur-md border border-secondary/30 rounded-2xl shadow-modal p-3.5 space-y-2 animate-float-delayed"
        >
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-secondary/15 text-secondary">
              <ShieldCheck className="w-4 h-4" />
            </div>
            <div>
              <div className="text-xs font-bold font-heading text-text">Tamper-Evident Ledger</div>
              <div className="text-[9px] font-mono text-muted">Block #24 Genesis Chain</div>
            </div>
          </div>

          <div className="p-2 rounded-xl bg-surface-alt font-mono text-[9px] text-muted space-y-0.5">
            <div className="truncate text-secondary font-bold">
              HASH: 0x8f2a...c94e
            </div>
            <div className="flex items-center justify-between text-[8px] text-success font-bold">
              <span>SHA-256 LEDGER VALID</span>
              <CheckCircle2 className="w-2.5 h-2.5" />
            </div>
          </div>
        </div>

        {/* Layer 4: Interactive Depth Badges */}
        <div
          style={{ transform: 'translateZ(95px) translateX(60px) translateY(150px)' }}
          className="absolute right-4 bottom-8 px-3 py-1.5 rounded-xl bg-hero-gradient text-white shadow-glow flex items-center gap-2 text-xs font-semibold font-sans"
        >
          <Eye className="w-3.5 h-3.5 text-secondary" />
          <span>Interactive 3D Scrutiny View</span>
        </div>
      </div>
    </div>
  );
};
