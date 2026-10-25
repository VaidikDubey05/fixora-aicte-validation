import React, { useEffect } from 'react';
import { X } from 'lucide-react';

interface DrawerProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
  width?: 'sm' | 'md' | 'lg' | 'xl' | 'full';
  position?: 'right' | 'left';
}

export const Drawer: React.FC<DrawerProps> = ({
  isOpen,
  onClose,
  title,
  subtitle,
  children,
  footer,
  width = 'md',
  position = 'right',
}) => {
  // Lock body scroll when drawer is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const widthClasses = {
    sm: 'max-w-sm',
    md: 'max-w-md',
    lg: 'max-w-lg',
    xl: 'max-w-2xl',
    full: 'max-w-full',
  };

  const positionClasses = {
    right: 'right-0 top-0 bottom-0 translate-x-0',
    left: 'left-0 top-0 bottom-0 translate-x-0',
  };

  return (
    <div className="fixed inset-0 z-50 overflow-hidden">
      {/* Backdrop with blur */}
      <div
        className="fixed inset-0 bg-[#0B0D1E]/50 backdrop-blur-sm transition-opacity duration-300"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Drawer Container */}
      <div className={`fixed inset-y-0 ${positionClasses[position]} max-w-full flex pl-0 sm:pl-10`}>
        <div
          className={`w-screen max-w-full ${widthClasses[width]} bg-surface border-l border-border shadow-modal flex flex-col transform transition-transform duration-300 ease-in-out`}
          role="dialog"
          aria-modal="true"
        >
          {/* Header */}
          <div className="p-5 border-b border-border flex items-start justify-between gap-4 bg-surface-alt/40">
            <div>
              <h3 className="text-base font-bold font-heading text-text">
                {title}
              </h3>
              {subtitle && (
                <p className="mt-0.5 text-xs text-muted font-sans">{subtitle}</p>
              )}
            </div>

            <button
              type="button"
              onClick={onClose}
              className="p-1.5 rounded-lg text-muted hover:text-text hover:bg-surface-alt border border-transparent hover:border-border transition-colors"
              aria-label="Close drawer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Body */}
          <div className="flex-1 overflow-y-auto p-5 space-y-4">
            {children}
          </div>

          {/* Optional Footer */}
          {footer && (
            <div className="p-4 border-t border-border bg-surface-alt/40">
              {footer}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
