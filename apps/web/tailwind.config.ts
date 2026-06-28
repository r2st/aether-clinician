import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Clinical severity / confidence palette.
        severity: {
          hard: '#b91c1c',
          critical: '#dc2626',
          warning: '#d97706',
          info: '#2563eb',
        },
        confidence: {
          high: '#16a34a',
          medium: '#d97706',
          low: '#dc2626',
        },
      },
    },
  },
  plugins: [],
};

export default config;
