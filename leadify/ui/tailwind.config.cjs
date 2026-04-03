/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', "Liberation Mono", "Courier New", 'monospace'],
      },
      colors: {
        bgMain: '#0e1117',
        bgPanel: '#161b22',
        borderSubtle: '#30363d',
        accentSubtle: '#21262d',
      }
    },
  },
  plugins: [],
}
