import React from 'react';
import { Check } from 'lucide-react';

export interface StepItem {
  id: string | number;
  title: string;
  description?: string;
  optional?: boolean;
}

interface StepperProps {
  steps: StepItem[];
  currentStep: number; // 0-indexed
  onStepClick?: (stepIndex: number) => void;
  className?: string;
}

export const Stepper: React.FC<StepperProps> = ({
  steps,
  currentStep,
  onStepClick,
  className = '',
}) => {
  return (
    <div className={`w-full overflow-x-auto py-2 ${className}`}>
      <ol className="flex items-center min-w-max">
        {steps.map((step, index) => {
          const isCompleted = index < currentStep;
          const isCurrent = index === currentStep;
          const isUpcoming = index > currentStep;

          return (
            <li
              key={step.id}
              className={`flex items-center ${
                index !== steps.length - 1 ? 'flex-1 pr-4' : ''
              }`}
            >
              <button
                type="button"
                onClick={() => onStepClick && onStepClick(index)}
                disabled={!onStepClick || isUpcoming}
                className={`flex items-center gap-3 text-left group focus:outline-none ${
                  onStepClick && !isUpcoming ? 'cursor-pointer' : 'cursor-default'
                }`}
              >
                <div
                  className={`w-9 h-9 rounded-xl flex items-center justify-center font-mono text-xs font-bold transition-all duration-300 border ${
                    isCompleted
                      ? 'bg-success text-white border-success shadow-xs'
                      : isCurrent
                      ? 'bg-hero-gradient text-white border-primary shadow-glow ring-4 ring-primary/15'
                      : 'bg-surface-alt text-muted border-border'
                  }`}
                >
                  {isCompleted ? <Check className="w-4 h-4 stroke-[2.5]" /> : index + 1}
                </div>

                <div className="flex flex-col">
                  <div className="flex items-center gap-1.5">
                    <span
                      className={`text-xs font-heading font-semibold transition-colors ${
                        isCurrent
                          ? 'text-primary'
                          : isCompleted
                          ? 'text-text'
                          : 'text-muted'
                      }`}
                    >
                      {step.title}
                    </span>
                    {step.optional && (
                      <span className="text-[10px] text-muted font-mono">(Optional)</span>
                    )}
                  </div>
                  {step.description && (
                    <span className="text-[11px] text-muted hidden sm:inline-block max-w-[140px] truncate">
                      {step.description}
                    </span>
                  )}
                </div>
              </button>

              {index !== steps.length - 1 && (
                <div
                  className={`flex-1 h-0.5 mx-3 rounded-full transition-all duration-300 ${
                    index < currentStep ? 'bg-success' : 'bg-border'
                  }`}
                />
              )}
            </li>
          );
        })}
      </ol>
    </div>
  );
};
