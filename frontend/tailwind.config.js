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
          bg: '#111315',
          panel: '#17191C',
          elevated: '#1D2024',
          secondary: '#202328',
          border: '#2A2E33',
          borderStrong: '#353A41',
          text: '#F2F3F5',
          textSecondary: '#9299A3',
          textMuted: '#646B75',
          paper: '#F8F7F3',
          paperSecondary: '#F1F0EB',
          accent: '#38C8B0',
          accentHover: '#4DD7C1',
        }
      }
    },
  },
  plugins: []
}
