import React from 'react';
import { Modal } from './Modal';
import { Command, ShieldCheck } from 'lucide-react';

interface KeyboardShortcutsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

interface ShortcutItem {
  keys: string[];
  description: string;
  scope: 'Global' | 'Review Workspace' | 'Navigation';
}

const SHORTCUTS: ShortcutItem[] = [
  { keys: ['Ctrl', 'K'], description: 'Open Global Command & Navigation Palette', scope: 'Global' },
  { keys: ['?'], description: 'Show this Keyboard Shortcuts cheat sheet', scope: 'Global' },
  { keys: ['T'], description: 'Toggle Light / Dark mode theme', scope: 'Global' },
  { keys: ['Esc'], description: 'Dismiss active modal, drawer, or command palette', scope: 'Global' },
  { keys: ['J'], description: 'Jump to Next Statutory Finding in Workspace', scope: 'Review Workspace' },
  { keys: ['K'], description: 'Jump to Previous Statutory Finding in Workspace', scope: 'Review Workspace' },
  { keys: ['C'], description: 'Confirm Active Finding (opens reason modal)', scope: 'Review Workspace' },
  { keys: ['D'], description: 'Dismiss Active Finding (opens reason modal)', scope: 'Review Workspace' },
  { keys: ['R'], description: 'Rotate active document page 90 degrees', scope: 'Review Workspace' },
];

export const KeyboardShortcutsModal: React.FC<KeyboardShortcutsModalProps> = ({
  isOpen,
  onClose,
}) => {
  const scopes = ['Global', 'Review Workspace'] as const;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Statutory Platform Keyboard Shortcuts"
      maxWidth="md"
    >
      <div className="space-y-5 py-1">
        <p className="text-xs text-muted font-sans">
          Boost your scrutiny and adjudication speed with instant keyboard shortcuts accessible across FIXORA.
        </p>

        {scopes.map((scope) => {
          const items = SHORTCUTS.filter((s) => s.scope === scope);
          return (
            <div key={scope} className="space-y-2">
              <h4 className="text-[11px] font-mono font-bold uppercase tracking-wider text-primary flex items-center gap-1.5">
                {scope === 'Global' ? <Command className="w-3.5 h-3.5" /> : <ShieldCheck className="w-3.5 h-3.5" />}
                <span>{scope} Shortcuts</span>
              </h4>
              <div className="bg-surface-alt/60 rounded-xl border border-border divide-y divide-border/60 overflow-hidden">
                {items.map((item, idx) => (
                  <div key={idx} className="p-2.5 flex items-center justify-between text-xs font-sans">
                    <span className="text-text font-medium">{item.description}</span>
                    <div className="flex items-center gap-1">
                      {item.keys.map((k, kIdx) => (
                        <kbd
                          key={kIdx}
                          className="px-2 py-0.5 rounded-md bg-surface border border-border text-[11px] font-mono font-bold text-text shadow-xs"
                        >
                          {k}
                        </kbd>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          );
        })}

        <div className="pt-2 text-right">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-xl text-xs font-semibold bg-primary text-white hover:bg-primary/90 transition-colors shadow-xs"
          >
            Got it (Esc)
          </button>
        </div>
      </div>
    </Modal>
  );
};
