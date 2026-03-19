/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        foundry: {
          bg: "#0a0a0a",
          surface: "#111111",
          border: "#1a1a1a",
          "border-light": "#2a2a2a",
          purple: "#9945FF",
          "purple-light": "#b366ff",
          "purple-dark": "#7a2ee6",
          green: "#14F195",
          "green-light": "#43f5ad",
          "green-dark": "#0cc77a",
          text: "#e5e5e5",
          "text-muted": "#888888",
          "text-dim": "#555555",
        },
      },
      fontFamily: {
        mono: ['"SF Mono"', "Fira Code", "Monaco", "Consolas", "monospace"],
        sans: ["Inter", "system-ui", "sans-serif"],
      },
      animation: {
        "pulse-glow": "pulse-glow 2s ease-in-out infinite",
        "fade-in": "fade-in 0.3s ease-out",
        "slide-up": "slide-up 0.3s ease-out",
        "slide-down": "slide-down 0.3s ease-out",
      },
      keyframes: {
        "pulse-glow": {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.6" },
        },
        "fade-in": {
          from: { opacity: "0" },
          to: { opacity: "1" },
        },
        "slide-up": {
          from: { opacity: "0", transform: "translateY(10px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        "slide-down": {
          from: { opacity: "0", transform: "translateY(-10px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
      },
    },
  },
  plugins: [],
};
