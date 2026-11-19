import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, ".", "");
  return {
    plugins: [react(), tailwindcss()],
    // amazon-cognito-identity-js espera la variable global de Node
    define: { global: "globalThis" },
    server: {
      // Solo en desarrollo: /api/* -> API Gateway (evita CORS desde localhost)
      proxy: env.VITE_API_PROXY_TARGET
        ? {
            "/api": {
              target: env.VITE_API_PROXY_TARGET,
              changeOrigin: true,
              rewrite: (path) => path.replace(/^\/api/, env.VITE_API_STAGE ?? ""),
            },
          }
        : undefined,
    },
  };
});
