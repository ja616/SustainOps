/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  safelist: [
    // Dynamic color classes used in ImpactBadge and other components
    { pattern: /bg-(brand|teal|orange|red|slate)-(500|900)\/(10|20|30|40)/ },
    { pattern: /text-(brand|teal|orange|red|slate)-(300|400|500)/ },
    { pattern: /border-(brand|teal|orange|red|slate)-(500|600)\/(20|30|40|50)/ },
    { pattern: /hover:border-(brand|teal|orange|red|slate)-(500|600)\/(40|50)/ },
    { pattern: /hover:bg-(brand|teal|orange|red|slate)-(500|900)\/(20|30)/ },
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50:  '#f0fdf4',
          100: '#dcfce7',
          400: '#4ade80',
          500: '#22c55e',
          600: '#16a34a',
          900: '#14532d',
        },
        dark: {
          bg:     '#0f172a',
          card:   '#1e293b',
          border: '#334155',
        },
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
      },
      keyframes: {
        'fade-in': {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'slide-up': {
          '0%': { opacity: '0', transform: 'translateY(20px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
      animation: {
        'fade-in':  'fade-in 0.3s ease-out',
        'slide-up': 'slide-up 0.4s ease-out',
      },
    },
  },
  plugins: [],
}
