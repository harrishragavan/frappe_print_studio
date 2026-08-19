import frappeUIPreset from 'frappe-ui/tailwind'

export default {
  presets: [frappeUIPreset],
  content: [
    './index.html',
    './src/**/*.{vue,js,ts,jsx,tsx}',
    './node_modules/frappe-ui/src/**/*.{vue,js,ts,jsx,tsx}',
    // INFO: uncomment the line below if you have workspaces set up
    // '../node_modules/frappe-ui/src/**/*.{vue,js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        studio: {
          bg: '#EFECE6',
          panel: '#FFFFFF',
          elevated: '#F8F6F2',
          secondary: '#F1EDE7',
          border: '#D1CDC7',
          borderStrong: '#AFA99E',
          text: '#2A2B2A',
          textSecondary: '#4B5E65',
          textMuted: '#8B867F',
          paper: '#FFFFFF',
          paperSecondary: '#FAF9F6',
          accent: '#F0533A',
          accentHover: '#F2735E',
        }
      }
    },
  },
  plugins: []
}
