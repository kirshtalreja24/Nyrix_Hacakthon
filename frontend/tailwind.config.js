/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Warm monochrome palette
        canvas: '#F7F6F3',
        surface: '#FFFFFF',
        border: '#EAEAEA',
        'text-primary': '#111111',
        'text-secondary': '#787774',
        'text-muted': '#A8A5A0',
        // Muted pastel accents
        'pale-red': '#FDEBEC',
        'pale-red-text': '#9F2F2D',
        'pale-blue': '#E1F3FE',
        'pale-blue-text': '#1F6C9F',
        'pale-green': '#EDF3EC',
        'pale-green-text': '#346538',
        'pale-yellow': '#FBF3DB',
        'pale-yellow-text': '#956400',
      },
      fontFamily: {
        sans: ['"SF Pro Display"', '"Helvetica Neue"', 'system-ui', 'sans-serif'],
        editorial: ['"Newsreader"', '"Playfair Display"', 'Georgia', 'serif'],
        mono: ['"SF Mono"', '"JetBrains Mono"', 'monospace'],
      },
      borderRadius: {
        'card': '8px',
      },
      boxShadow: {
        'subtle': '0 1px 3px rgba(0,0,0,0.03)',
        'lift': '0 2px 8px rgba(0,0,0,0.04)',
      },
      animation: {
        'fade-in': 'fadeIn 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards',
        'fade-up': 'fadeUp 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards',
        'ambient': 'ambient 20s ease-in-out infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        fadeUp: {
          '0%': { opacity: '0', transform: 'translateY(12px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        ambient: {
          '0%, 100%': { transform: 'translate(0, 0) scale(1)' },
          '50%': { transform: 'translate(30px, -20px) scale(1.1)' },
        },
      },
    },
  },
  plugins: [],
}
