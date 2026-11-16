/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        navy: {
          950: '#040B14',
          900: '#0B192C',
          850: '#0F213A',
          800: '#142742',
          700: '#1B355A',
          600: '#234473',
          500: '#325C99',
          100: '#E6EDF5',
          50: '#F0F5FA'
        },
        burgundy: {
          950: '#2B060C',
          900: '#4A0E17',
          850: '#5A121D',
          800: '#6C1A25',
          700: '#842230',
          600: '#9E2C3D',
          100: '#F9EBEB',
          50: '#FDF6F6'
        },
        ivory: {
          50: '#FCFAF6',
          100: '#FAF7F2',
          200: '#F4EFE6',
          300: '#EBE2D3',
          400: '#DECDB5'
        },
        gold: {
          900: '#5C441E',
          800: '#7A5B28',
          700: '#997334',
          600: '#B88B40',
          500: '#C5A880',
          400: '#D6C09F',
          300: '#E5D6C1',
          200: '#F2ECE1',
          100: '#F9F6F0'
        },
        charcoal: {
          900: '#151311',
          800: '#1C1917',
          700: '#2D2825',
          600: '#443E3A',
          500: '#635B55',
          400: '#8A827B',
          300: '#B5AEA7',
          200: '#DCD7D1',
          100: '#F2EFEB'
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        serif: ['Cinzel', 'Merriweather', 'Georgia', 'Cambria', 'serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'Courier New', 'monospace']
      },
      boxShadow: {
        'judicial': '0 4px 20px -2px rgba(11, 25, 44, 0.08), 0 2px 6px -1px rgba(11, 25, 44, 0.04)',
        'judicial-lg': '0 10px 30px -4px rgba(11, 25, 44, 0.12), 0 4px 12px -2px rgba(11, 25, 44, 0.06)',
        'gold-glow': '0 0 15px -3px rgba(197, 168, 128, 0.35)'
      }
    },
  },
  plugins: [],
}
