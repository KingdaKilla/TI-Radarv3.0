import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        radar: {
          50: "#e8edf4",
          100: "#c8d5e8",
          200: "#8899aa",
          300: "#4a5f78",
          400: "#1e3350",
          500: "#132238",
          600: "#0d1b2a",
          700: "#091428",
          800: "#060e1c",
          900: "#040a14",
          950: "#020610",
        },
        teal: {
          400: "#48cae4",
          500: "#00b4d8",
          600: "#0891b2",
        },
        gold: {
          400: "#e6be6a",
          500: "#d4a853",
          600: "#b8860b",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
