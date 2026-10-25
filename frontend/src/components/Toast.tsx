import React, { useEffect } from 'react';
import { CheckCircle2, AlertTriangle, AlertCircle, Info, X } from 'lucide-react';

export type ToastType = 'success' | 'warning' | 'danger' | 'info';

export interface ToastMessage {
  id: string;
  type: ToastType;
  title: string;
  message?: string;
  duration?: number;
}

interface ToastProps {
  toast: ToastMessage;
  onDismiss: (id: string) => void;
}

export const Toast: React.FC<ToastProps> = ({ toast, onDismiss }) => {
  useEffect(() => {
    if (toast.duration !== 0) {
      const timer = setTimeout(() => {
        onDismiss(toast.id);
      }, toast.duration || 4500);
      return () => clearTimeout(timer);
    }
  }, [toast, onDismiss]);

  const config = {
    success: {
      icon: CheckCircle2,
      border: 'border-success/40',
      iconColor: 'text-success',
      bg: 'bg-surface',
    },
    warning: {
      icon: AlertTriangle,
      border: 'border-warning/40',
      iconColor: 'text-warning',
      bg: 'bg-surface',
    },
    danger: {
      icon: AlertCircle,
      border: 'border-danger/40',
      iconColor: 'text-danger',
      bg: 'bg-surface',
    },
    info: {
      icon: Info,
      border: 'border-info/40',
      iconColor: 'text-info',
      bg: 'bg-surface',
    },
  }[toast.type];

  const Icon = config.icon;

  return (
    <div
      className={`flex items-start gap-3 p-4 rounded-xl border ${config.border} ${config.bg} shadow-floating max-w-sm w-full transition-all transform animate-in slide-in-from-top-2 duration-300 pointer-events-auto`}
      role="alert"
    >
      <Icon className={`w-5 h-5 flex-shrink-0 mt-0.5 ${config.iconColor}`} />
      
      <div className="flex-1 min-w-0">
        <h5 className="text-xs font-bold font-heading text-text">
          {toast.title}
        </h5>
        {toast.message && (
          <p className="mt-1 text-xs text-muted leading-relaxed font-sans">
            {toast.message}
          </p>
        )}
      </div>

      <button
        type="button"
        onClick={() => onDismiss(toast.id)}
        className="p-1 rounded-md text-muted hover:text-text hover:bg-surface-alt transition-colors"
        aria-label="Dismiss toast"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  );
};

export const ToastContainer: React.FC<{
  toasts: ToastMessage[];
  onDismiss: (id: string) => void;
}> = ({ toasts, onDismiss }) => {
  if (toasts.length === 0) return null;

  return (
    <div className="fixed top-5 right-5 z-50 flex flex-col gap-2 pointer-events-none">
      {toasts.map((toast) => (
        <Toast key={toast.id} toast={toast} onDismiss={onDismiss} />
      ))}
    </div>
  );
};
