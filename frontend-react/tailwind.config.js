/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      // Design system: UI/UX Pro Max — Flat Design, teal primary + orange accent.
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'ui-sans-serif', 'system-ui', 'Segoe UI', 'sans-serif'],
      },
      colors: {
        // brand = teal scale (primary)
        brand: {
          50: '#f0fdfa', 100: '#ccfbf1', 200: '#99f6e4', 300: '#5eead4',
          400: '#2dd4bf', 500: '#14b8a6', 600: '#0d9488', 700: '#0f766e',
        },
        // accent = orange (CTA)
        accent: { 400: '#fb923c', 500: '#f97316', 600: '#ea580c', 700: '#c2410c' },
        ink: '#134e4a',        // foreground
        canvas: '#f0fdfa',     // background
      },
      keyframes: {
        'fade-up': { '0%': { opacity: 0, transform: 'translateY(6px)' }, '100%': { opacity: 1, transform: 'none' } },
      },
      animation: { 'fade-up': 'fade-up .18s ease-out' },
    },
  },
  plugins: [],
}
