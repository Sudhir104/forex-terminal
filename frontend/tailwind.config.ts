import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0A0E12",
        panel: "#12181F",
        panel2: "#171F28",
        line: "#232D38",
        ink: "#E7ECEF",
        muted: "#8A97A3",
        gold: "#D9A441",
        pos: "#4FAE7A",
        neg: "#C6564B",
        steel: "#5B7A96",
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
};
export default config;
