import type { Config } from 'tailwindcss';

const config: Config = {
  darkMode: 'class',
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#5B5BFF',
          hover: '#4A4AE8',
          light: '#EBEBFF',
          dark: '#403DE6',
        },
        secondary: {
          DEFAULT: '#00D1C1',
          hover: '#00B8A9',
          light: '#E6FAF8',
          dark: '#006A62',
        },
        accent: {
          DEFAULT: '#FFB800',
          hover: '#E5A600',
          light: '#FFF8E6',
        },
        success: {
          DEFAULT: '#22C55E',
          hover: '#16A34A',
          light: '#DCFCE7',
          dark: '#15803D',
        },
        warning: {
          DEFAULT: '#FF8A1F',
          hover: '#EA580C',
          light: '#FFF7ED',
          dark: '#C25E00',
        },
        danger: {
          DEFAULT: '#FF4D6D',
          hover: '#E11D48',
          light: '#FFE4E6',
          dark: '#DC2626',
        },
        info: {
          DEFAULT: '#2DA8FF',
          hover: '#0284C7',
          light: '#E0F2FE',
        },
        bg: 'var(--bg)',
        surface: 'var(--surface)',
        'surface-alt': 'var(--surface-alt)',
        border: 'var(--border)',
        text: 'var(--text)',
        muted: 'var(--muted)',
      },
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'Inter', 'sans-serif'],
        heading: ['"Plus Jakarta Sans"', 'sans-serif'],
        body: ['Inter', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      borderRadius: {
        sm: '0.25rem',
        DEFAULT: '0.5rem',
        md: '0.75rem',
        lg: '1rem',
        xl: '1.5rem',
        '2xl': '2rem',
        full: '9999px',
        card: '16px',
        input: '12px',
      },
      boxShadow: {
        card: '0 1px 3px rgba(20, 23, 47, 0.03), 0 8px 24px -4px rgba(91, 93, 255, 0.06)',
        floating: '0 12px 32px -6px rgba(20, 23, 47, 0.12)',
        modal: '0 24px 48px -12px rgba(20, 23, 47, 0.18)',
        glow: '0 4px 14px rgba(91, 91, 255, 0.35)',
      },
      backgroundImage: {
        'hero-gradient': 'linear-gradient(135deg, #5B5BFF 0%, #A855F7 100%)',
      },
    },
  },
  plugins: [],
};

export default config;
