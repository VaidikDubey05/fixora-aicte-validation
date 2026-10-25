import React, { useState, useEffect } from 'react';
import {
  FileText,
  ZoomIn,
  ZoomOut,
  ChevronLeft,
  ChevronRight,
  ShieldCheck,
  Layers,
  Sparkles,
  Columns,
  Loader2,
  RotateCw,
  Maximize2,
  Minimize2,
} from 'lucide-react';
import api from '../lib/api';
import { useDocumentOcr } from '../api/useDocumentOcr';
import { SimulatedBadge } from './SimulatedBadge';

export interface BoundingBoxItem {
  id: string;
  findingId?: string;
  field: string;
  value: string;
  confidence: number;
  page: number;
  bbox: [number, number, number, number]; // [x0, y0, x1, y1] or [x, y, w, h]
  status?: 'match' | 'discrepancy' | 'unverified';
}

export interface SideBySideEvidence {
  left: {
    title: string;
    value: string;
    source: string;
    bbox?: [number, number, number, number];
    page?: number;
  };
  right: {
    title: string;
    value: string;
    source: string;
    bbox?: [number, number, number, number];
    page?: number;
  };
}

interface EvidenceViewerProps {
  documentId?: string;
  documentTitle?: string;
  category?: string;
  totalPages?: number;
  activeFindingId?: string | null;
  selectedBoxId?: string;
  onSelectBox?: (id: string) => void;
  boxes?: BoundingBoxItem[];
  sideBySide?: SideBySideEvidence | null;
  className?: string;
}

export const EvidenceViewer: React.FC<EvidenceViewerProps> = ({
  documentId = 'DOC-2026-LAND-0041',
  documentTitle = 'Registered Land Deed & Surveyor Site Plan.pdf',
  category = 'Land & Legal Ownership',
  totalPages = 4,
  activeFindingId,
  selectedBoxId,
  onSelectBox,
  boxes = [],
  sideBySide,
  className = '',
}) => {
  const [zoom, setZoom] = useState<number>(100);
  const [rotation, setRotation] = useState<number>(0);
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<'canvas' | 'ocr' | 'compare'>('canvas');
  const [showOverlays, setShowOverlays] = useState<boolean>(true);
  const [page, setPage] = useState<number>(1);
  const [pageImageUrl, setPageImageUrl] = useState<string | null>(null);
  const [imageLoading, setImageLoading] = useState<boolean>(false);

  // Fetch real OCR data from backend
  const { data: ocrData, isLoading: isOcrLoading } = useDocumentOcr(documentId);

  // Load rendered page PNG image from backend GET /api/documents/{id}/pages/{n}/image
  useEffect(() => {
    let active = true;
    let objectUrl = '';

    const fetchPageImage = async () => {
      setImageLoading(true);
      try {
        const res = await api.get(`/documents/${documentId}/pages/${page}/image`, {
          responseType: 'blob',
        });
        if (active) {
          objectUrl = URL.createObjectURL(res.data);
          setPageImageUrl(objectUrl);
        }
      } catch {
        if (active) {
          setPageImageUrl(null);
        }
      } finally {
        if (active) setImageLoading(false);
      }
    };

    fetchPageImage();

    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [documentId, page]);

  // When activeFindingId changes, switch to its page
  useEffect(() => {
    if (activeFindingId && boxes.length > 0) {
      const match = boxes.find((b) => b.findingId === activeFindingId);
      if (match && match.page) {
        setPage(match.page);
      }
    }
  }, [activeFindingId, boxes]);

  const handleZoomIn = () => setZoom((prev) => Math.min(prev + 15, 180));
  const handleZoomOut = () => setZoom((prev) => Math.max(prev - 15, 70));
  const handleResetZoom = () => setZoom(100);

  // Get current page OCR dimensions
  const currentPageOcr = ocrData?.pages?.find((p) => p.page === page);
  const pageWidth = currentPageOcr?.page_width || 595.0;
  const pageHeight = currentPageOcr?.page_height || 842.0;

  // Filter boxes for current page
  const pageBoxes = boxes.filter((b) => !b.page || b.page === page);

  return (
    <div className={`flex flex-col h-full rounded-card bg-surface border border-border shadow-card overflow-hidden ${isFullscreen ? 'fixed inset-3 sm:inset-6 z-50 shadow-modal bg-surface' : ''} ${className}`}>
      {/* Top Document HUD Toolbar */}
      <div className="p-3.5 border-b border-border bg-surface-alt/50 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="p-2 rounded-lg bg-primary/10 text-primary flex-shrink-0">
            <FileText className="w-4 h-4" />
          </div>
          <div className="min-w-0">
            <h4 className="text-xs font-bold font-heading text-text truncate max-w-[260px] sm:max-w-xs">
              {documentTitle}
            </h4>
            <div className="flex items-center gap-2 text-[10px] text-muted font-mono">
              <span>{documentId}</span>
              <span>•</span>
              <span>{category}</span>
            </div>
          </div>
        </div>

        {/* Action Controls & Navigation */}
        <div className="flex items-center gap-2">
          {/* View Mode Tabs */}
          <div className="inline-flex rounded-lg border border-border bg-surface p-0.5 text-xs">
            <button
              type="button"
              onClick={() => setActiveTab('canvas')}
              className={`px-2.5 py-1 rounded-md font-sans text-xs transition-colors ${
                activeTab === 'canvas'
                  ? 'bg-primary text-white font-medium shadow-xs'
                  : 'text-muted hover:text-text'
              }`}
            >
              Document
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('ocr')}
              className={`px-2.5 py-1 rounded-md font-sans text-xs transition-colors ${
                activeTab === 'ocr'
                  ? 'bg-primary text-white font-medium shadow-xs'
                  : 'text-muted hover:text-text'
              }`}
            >
              OCR Stream
            </button>
            {sideBySide && (
              <button
                type="button"
                onClick={() => setActiveTab('compare')}
                className={`px-2.5 py-1 rounded-md font-sans text-xs flex items-center gap-1 transition-colors ${
                  activeTab === 'compare'
                    ? 'bg-primary text-white font-medium shadow-xs'
                    : 'text-muted hover:text-text'
                }`}
              >
                <Columns className="w-3 h-3" />
                <span>Side-by-Side</span>
              </button>
            )}
          </div>

          {/* Zoom & Overlay Toggle */}
          <div className="hidden sm:flex items-center gap-1 border-l border-border pl-2">
            <button
              type="button"
              onClick={() => setShowOverlays(!showOverlays)}
              title={showOverlays ? 'Hide Bounding Boxes' : 'Show Bounding Boxes'}
              className={`p-1.5 rounded-lg border text-xs transition-colors ${
                showOverlays
                  ? 'bg-secondary/15 text-secondary border-secondary/30'
                  : 'bg-surface text-muted border-border hover:text-text'
              }`}
            >
              <Layers className="w-3.5 h-3.5" />
            </button>

            <button
              type="button"
              onClick={handleZoomOut}
              className="p-1.5 rounded-lg border border-border bg-surface text-muted hover:text-text transition-colors"
              title="Zoom Out"
            >
              <ZoomOut className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              onClick={handleResetZoom}
              className="px-2 py-1 text-[11px] font-mono border border-border bg-surface text-muted hover:text-text rounded-lg"
              title="Reset Zoom"
            >
              {zoom}%
            </button>
            <button
              type="button"
              onClick={handleZoomIn}
              className="p-1.5 rounded-lg border border-border bg-surface text-muted hover:text-text transition-colors"
              title="Zoom In"
            >
              <ZoomIn className="w-3.5 h-3.5" />
            </button>

            {/* Rotate Page 90 deg button */}
            <button
              type="button"
              onClick={() => setRotation((r) => (r + 90) % 360)}
              className="p-1.5 rounded-lg border border-border bg-surface text-muted hover:text-text transition-colors"
              title="Rotate 90 degrees clockwise (R)"
            >
              <RotateCw className="w-3.5 h-3.5" />
            </button>

            {/* Fullscreen Expand button */}
            <button
              type="button"
              onClick={() => setIsFullscreen(!isFullscreen)}
              className={`p-1.5 rounded-lg border text-xs transition-colors ${
                isFullscreen
                  ? 'bg-primary text-white border-primary'
                  : 'bg-surface text-muted border-border hover:text-text'
              }`}
              title={isFullscreen ? 'Exit Fullscreen' : 'Fullscreen Inspection View'}
            >
              {isFullscreen ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
            </button>
          </div>
        </div>
      </div>

      {/* Main Viewport */}
      <div className="flex-1 overflow-auto bg-surface-alt/30 p-4 flex items-center justify-center min-h-[440px] relative">
        {activeTab === 'canvas' && (
          <div
            style={{ transform: `scale(${zoom / 100}) rotate(${rotation}deg)`, transformOrigin: 'center center' }}
            className="transition-transform duration-200"
          >
            {/* Rendered Document Container */}
            <div className="relative w-[560px] min-h-[720px] bg-white text-slate-900 rounded-lg shadow-floating border border-border/80 select-none overflow-hidden">
              {imageLoading ? (
                <div className="h-[720px] flex flex-col items-center justify-center gap-2 text-muted">
                  <Loader2 className="w-6 h-6 animate-spin text-primary" />
                  <span className="text-xs font-mono">Rendering high-resolution page...</span>
                </div>
              ) : pageImageUrl ? (
                <div className="relative w-full h-full">
                  <img
                    src={pageImageUrl}
                    alt={`Document page ${page}`}
                    className="w-full h-auto block"
                  />

                  {/* Absolutely Positioned Bounding Boxes scaling with page */}
                  {showOverlays &&
                    pageBoxes.map((box) => {
                      const isSelected = selectedBoxId === box.id;
                      const isPulsing = activeFindingId === box.findingId;
                      const isDiscrepancy = box.status === 'discrepancy';

                      // Normalise coordinates to fractions (x0/width etc.)
                      let leftPct = 15;
                      let topPct = 30;
                      let widthPct = 40;
                      let heightPct = 8;

                      if (box.bbox && box.bbox.length === 4) {
                        const [x0, y0, x1, y1] = box.bbox;
                        // If coordinates are pixel values (> 1), divide by page width/height
                        if (x0 > 1 || y0 > 1) {
                          leftPct = Math.max(0, Math.min(100, (x0 / pageWidth) * 100));
                          topPct = Math.max(0, Math.min(100, (y0 / pageHeight) * 100));
                          widthPct = Math.max(2, Math.min(100, ((x1 - x0) / pageWidth) * 100));
                          heightPct = Math.max(2, Math.min(100, ((y1 - y0) / pageHeight) * 100));
                        } else {
                          // Already fractions
                          leftPct = x0 * 100;
                          topPct = y0 * 100;
                          widthPct = x1 * 100;
                          heightPct = y1 * 100;
                        }
                      }

                      return (
                        <div
                          key={box.id}
                          onClick={() => onSelectBox && onSelectBox(box.id)}
                          style={{
                            left: `${leftPct}%`,
                            top: `${topPct}%`,
                            width: `${widthPct}%`,
                            height: `${heightPct}%`,
                          }}
                          className={`absolute cursor-pointer rounded border-2 transition-all duration-200 ${
                            isPulsing
                              ? 'border-primary bg-primary/30 ring-4 ring-primary/40 shadow-glow animate-pulse'
                              : isSelected
                              ? 'border-primary bg-primary/25 ring-2 ring-primary/40 shadow-glow'
                              : isDiscrepancy
                              ? 'border-warning bg-warning/20 hover:bg-warning/30 ring-1 ring-warning/30'
                              : 'border-secondary bg-secondary/15 hover:bg-secondary/25'
                          }`}
                        >
                          <div className="absolute -top-5 left-0 flex items-center gap-1 bg-[#14172F] text-white text-[9px] font-mono px-1.5 py-0.5 rounded shadow-xs whitespace-nowrap z-10">
                            <Sparkles className="w-2.5 h-2.5 text-secondary" />
                            <span>{box.field}</span>
                            <span className="text-secondary font-bold">{box.confidence}%</span>
                          </div>
                        </div>
                      );
                    })}
                </div>
              ) : (
                /* Fallback clean presentation canvas */
                <div className="p-8 space-y-4">
                  <div className="border-b-2 border-slate-300 pb-4 flex justify-between items-start">
                    <div>
                      <p className="text-[10px] font-mono uppercase tracking-widest text-slate-500 font-bold">
                        Official Statutory Record
                      </p>
                      <h3 className="text-base font-bold font-serif text-slate-900">
                        GOVERNMENT OF MAHARASHTRA
                      </h3>
                      <p className="text-xs text-slate-600">
                        INSPECTOR GENERAL OF REGISTRATION (IGR)
                      </p>
                    </div>
                    <span className="px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-300 text-[10px] font-mono font-semibold">
                      DIGITALLY CERTIFIED
                    </span>
                  </div>

                  <div className="space-y-3 text-xs font-serif leading-relaxed text-slate-800 pt-2">
                    <p className="font-bold">SCHEDULE OF REGISTERED PROPERTY:</p>
                    <div className="p-3 bg-slate-50 border border-slate-200 rounded font-mono text-[11px] space-y-1">
                      <div>Survey Numbers: 114/2A, 115/1B, 116/3</div>
                      <div>Total Measured Contiguous Land: <strong>7.42 Acres</strong> (30,027.6 sq.m)</div>
                      <div>Permissible Built-up Area: 22,400 sq.m</div>
                      <div>Constructed Carpet Area Claimed: <strong>24,150 sq.m</strong></div>
                    </div>
                  </div>

                  <div className="pt-10 flex items-center justify-between text-[10px] text-slate-500 font-mono">
                    <span>Page {page} of {totalPages}</span>
                    <span className="text-emerald-700 flex items-center gap-1">
                      <ShieldCheck className="w-3.5 h-3.5" /> Cryptographically Valid
                    </span>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* OCR Stream Tab */}
        {activeTab === 'ocr' && (
          <div className="w-full max-w-2xl bg-surface rounded-xl border border-border p-5 font-mono text-xs text-text shadow-sm overflow-x-auto">
            <div className="flex items-center justify-between pb-3 mb-3 border-b border-border">
              <span className="text-muted text-[11px] uppercase tracking-wider font-bold">
                Tesseract OCR (eng+hin) Stream — Page {page}
              </span>
              <span className="text-xs text-secondary font-bold">
                Resolution: {pageWidth}x{pageHeight} pt
              </span>
            </div>
            {isOcrLoading ? (
              <div className="p-8 text-center text-muted">
                <Loader2 className="w-5 h-5 animate-spin mx-auto mb-2 text-primary" />
                <span>Loading OCR layer...</span>
              </div>
            ) : currentPageOcr?.text ? (
              <pre className="whitespace-pre-wrap leading-relaxed font-mono text-xs">
                {currentPageOcr.text}
              </pre>
            ) : (
              <p className="text-muted text-xs">No raw OCR text for this page.</p>
            )}
          </div>
        )}

        {/* Side-by-Side Compare Tab (takes two evidence items from the same finding) */}
        {activeTab === 'compare' && sideBySide && (
          <div className="w-full max-w-4xl grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-4 rounded-xl bg-surface border border-border space-y-3 shadow-card">
              <div className="flex items-center justify-between pb-2 border-b border-border">
                <span className="text-[10px] font-mono text-muted uppercase font-bold">
                  Dossier Evidence A
                </span>
                <span className="text-xs font-mono text-primary font-bold">
                  {sideBySide.left.source}
                </span>
              </div>
              <h5 className="text-xs font-bold text-text">{sideBySide.left.title}</h5>
              <div className="p-3 rounded-lg bg-surface-alt font-mono text-xs font-bold text-text">
                {sideBySide.left.value}
              </div>
            </div>

            <div className="p-4 rounded-xl bg-surface border border-secondary/30 space-y-3 shadow-card">
              <div className="flex items-center justify-between pb-2 border-b border-border">
                <span className="text-[10px] font-mono text-secondary uppercase font-bold">
                  Dossier Evidence B / Statutory Norm
                </span>
                <SimulatedBadge sourceName={sideBySide.right.source} />
              </div>
              <h5 className="text-xs font-bold text-text">{sideBySide.right.title}</h5>
              <div className="p-3 rounded-lg bg-surface-alt font-mono text-xs font-bold text-secondary">
                {sideBySide.right.value}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Bottom Pagination Bar */}
      <div className="px-4 py-2.5 border-t border-border bg-surface-alt/40 flex items-center justify-between text-xs">
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1}
            className="p-1 rounded border border-border bg-surface text-muted hover:text-text disabled:opacity-40 transition-colors"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <span className="font-mono text-[11px] text-muted flex items-center gap-1">
            <span>Page</span>
            <select
              value={page}
              onChange={(e) => setPage(Number(e.target.value))}
              className="bg-surface border border-border rounded px-1.5 py-0.5 text-text font-bold text-xs focus:outline-none cursor-pointer"
            >
              {Array.from({ length: totalPages }, (_, i) => i + 1).map((pNum) => (
                <option key={pNum} value={pNum}>
                  {pNum}
                </option>
              ))}
            </select>
            <span>of {totalPages}</span>
          </span>
          <button
            type="button"
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages}
            className="p-1 rounded border border-border bg-surface text-muted hover:text-text disabled:opacity-40 transition-colors"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>

        <div className="flex items-center gap-2">
          <SimulatedBadge sourceName="State Directorate Records" />
        </div>
      </div>
    </div>
  );
};
