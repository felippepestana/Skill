import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // APEX-LEGAL brand palette: azul jurídico + dourado
        apex: {
          50:  "#f0f4ff",
          100: "#dce6ff",
          200: "#b8ccff",
          300: "#84a4ff",
          400: "#4d73ff",
          500: "#1a47ff",
          600: "#0030e8",
          700: "#0026c0",
          800: "#00209a",
          900: "#001878",
          950: "#000e4d",
        },
        gold: {
          400: "#f5c842",
          500: "#e8b200",
          600: "#c49500",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
        serif: ["Georgia", "serif"],
      },
    },
  },
  plugins: [require("@tailwindcss/typography")],
};

export default config;
