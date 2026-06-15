/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        // EMS energy palette
        navy: { DEFAULT: "#0F3D57", deep: "#071923", panel: "#0B1220" },
        energy: "#16A34A", // green energy
        solar: "#F59E0B", // solar yellow
        electric: "#2563EB", // electric blue
        danger: "#DC2626", // alert red
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      boxShadow: {
        card: "0 1px 3px rgba(15,61,87,0.08), 0 1px 2px rgba(15,61,87,0.06)",
      },
    },
  },
  plugins: [],
};
