import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  // amazon-cognito-identity-js espera la variable global de Node
  define: { global: "globalThis" },
});
