/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['DM Sans', 'sans-serif'],
      },
      keyframes: {
        pulse_dot: {
          '0%, 100%': { opacity: 1 },
          '50%': { opacity: 0.3 },
        },
        slide_in_right: {
          from: { transform: 'translateX(100%)' },
          to: { transform: 'translateX(0)' },
        },
        slide_in_top: {
          from: { transform: 'translateX(100%)', opacity: 0 },
          to: { transform: 'translateX(0)', opacity: 1 },
        },
        fade_out: {
          from: { opacity: 1 },
          to: { opacity: 0 },
        },
      },
      animation: {
        pulse_dot: 'pulse_dot 1.5s ease-in-out infinite',
        slide_in_right: 'slide_in_right 0.3s ease-out',
        slide_in_top: 'slide_in_top 0.3s ease-out',
        fade_out: 'fade_out 0.3s ease-in forwards',
      },
    },
  },
  plugins: [],
}
