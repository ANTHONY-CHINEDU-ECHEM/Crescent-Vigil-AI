import { defineConfig } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";
import { viteSingleFile } from "vite-plugin-singlefile";

export default defineConfig(({ mode }) => ({
  base: "./",
  plugins: [svelte(), ...(mode === "single" ? [viteSingleFile()] : [])],
  build: { outDir: mode === "single" ? "dist_single" : "dist", target: "es2022", chunkSizeWarningLimit: 4000 },
  server: { proxy: { "/api": "http://localhost:8000" } },
  test: { include: ["tests/**/*.test.ts"], testTimeout: 120000 },
}));
