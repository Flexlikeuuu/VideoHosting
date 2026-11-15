/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        yt: {
          red: '#FF0000',
          dark: '#0f0f0f',
          darkSec: '#272727',
          darkHover: '#3f3f3f',
          darkCard: '#1f1f1f',
          light: '#ffffff',
          lightSec: '#f2f2f2',
          lightHover: '#e5e5e5',
        }
      }
    },
  },
  plugins: [],
}
