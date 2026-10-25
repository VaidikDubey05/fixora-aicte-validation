import React from 'react';

interface ConfidenceRingProps {
  score: number; // 0 to 100 or 0 to 1
  size?: number;
  strokeWidth?: number;
  showLabel?: boolean;
  className?: string;
}

export const ConfidenceRing: React.FC<ConfidenceRingProps> = ({
  score,
  size = 48,
  strokeWidth = 4,
  showLabel = true,
  className = '',
}) => {
  // Normalize score to percentage 0-100
  const normalizedScore = Math.min(100, Math.max(0, score <= 1 ? Math.round(score * 100) : Math.round(score)));
  
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (normalizedScore / 100) * circumference;

  // Determine color based on threshold
  let strokeColor = '#22C55E'; // success
  let textColor = 'text-success';
  if (normalizedScore < 70) {
    strokeColor = '#FF4D6D'; // danger / low confidence
    textColor = 'text-danger';
  } else if (normalizedScore < 85) {
    strokeColor = '#FF8A1F'; // warning / moderate
    textColor = 'text-warning';
  }

  return (
    <div className={`relative inline-flex items-center justify-center ${className}`} style={{ width: size, height: size }}>
      <svg width={size} height={size} className="transform -rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="currentColor"
          strokeWidth={strokeWidth}
          className="text-border"
          fill="transparent"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={strokeColor}
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          fill="transparent"
          className="transition-all duration-700 ease-out"
        />
      </svg>
      {showLabel && (
        <span className={`absolute text-[11px] font-mono font-bold ${textColor}`}>
          {normalizedScore}%
        </span>
      )}
    </div>
  );
};
