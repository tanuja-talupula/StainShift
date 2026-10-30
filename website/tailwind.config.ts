import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        serif: [
          "Newsreader",
          "Charter",
          "Bitstream Charter",
          "Sitka Text",
          "Cambria",
          "Georgia",
          "serif",
        ],
        sans: [
          "Inter",
          "-apple-system",
          "BlinkMacSystemFont",
          '"Segoe UI"',
          "Roboto",
          '"Helvetica Neue"',
          "Arial",
          "sans-serif",
        ],
        mono: [
          "JetBrains Mono",
          "ui-monospace",
          "SFMono-Regular",
          "Menlo",
          "Monaco",
          "Consolas",
          "monospace",
        ],
      },
      colors: {
        cream: {
          50: "#FCFAF7",
          100: "#FAF8F5", // primary background
          200: "#F4EFEA", // warm card surface
          300: "#EDE7DE",
          400: "#E2DDD3",
          500: "#D3CCC0",
        },
        charcoal: {
          950: "#141312",
          900: "#1A1918", // near-black primary text
          800: "#272523",
          700: "#3D3A37",
          600: "#5A5650",
          500: "#757067", // secondary body
          400: "#969086",
          300: "#B8B2A7",
          200: "#DDD8CF",
          100: "#EDE9E1",
          50: "#F6F4EF",
        },
        terracotta: {
          50: "#FBF5F1",
          100: "#F6ECE4",
          200: "#EDD7C7",
          300: "#DFBAA3",
          400: "#D3977B",
          500: "#CC785C", // Claude iconic warm terracotta
          600: "#B86348",
          700: "#9B4E37",
          800: "#7B3B29",
          900: "#5C2B1D",
        },
        warmborder: {
          DEFAULT: "#E8E4DD",
          subtle: "#EFEBE4",
          strong: "#D8D2C6",
        },
        // Brand aliases for compatibility
        brand: {
          50: "#FBF5F1",
          100: "#F6ECE4",
          200: "#EDD7C7",
          500: "#CC785C",
          600: "#1A1918", // button primary is sleek charcoal
          700: "#272523",
          800: "#141312",
          900: "#1A1918",
        },
        sage: {
          50: "#F3F7F4",
          100: "#E5EDE7",
          600: "#2E5E48",
          700: "#234938",
        },
      },
      boxShadow: {
        warm: "0 1px 3px 0 rgba(30, 25, 20, 0.04), 0 1px 2px -1px rgba(30, 25, 20, 0.04)",
        "warm-md": "0 4px 6px -1px rgba(30, 25, 20, 0.05), 0 2px 4px -2px rgba(30, 25, 20, 0.05)",
      },
    },
  },
  plugins: [],
};

export default config;
