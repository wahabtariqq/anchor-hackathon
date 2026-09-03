/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: { "2xl": "1400px" },
    },
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        "anchor-good": "hsl(var(--anchor-good))",
        "anchor-critical": "hsl(var(--anchor-critical))",
        "anchor-adjacent": "hsl(var(--anchor-adjacent))",
        "anchor-ring-fill": "hsl(var(--anchor-ring-fill))",
        "anchor-ring-track": "hsl(var(--anchor-ring-track))",
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
        "token-sm": "var(--radius-sm)",
        "token-md": "var(--radius-md)",
        "token-lg": "var(--radius-lg)",
      },
      fontFamily: {
        display: ["var(--font-display)"],
      },
      fontSize: {
        display: ["var(--text-display)", { fontWeight: "600" }],
        heading: ["var(--text-heading)", { fontWeight: "600" }],
        body: ["var(--text-body)", { fontWeight: "400" }],
        caption: ["var(--text-caption)", { fontWeight: "500" }],
      },
      // Spacing: Tailwind's default 4px-increment scale already equals --space-1..8
      // (anchor-design §4) — p-1/p-2/p-3/p-4/p-6/p-8 ARE the token scale, no extension needed.
    },
  },
  plugins: [require("tailwindcss-animate")],
};
