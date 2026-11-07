import { defineConfig, devices } from "@playwright/test";

/** Corre contra Vite con el backend de Docker en :8080. Ver e2e/README.md. */
export default defineConfig({
  testDir: "e2e",
  outputDir: "e2e/.results",
  fullyParallel: false,
  workers: 1,
  timeout: 45_000,
  reporter: "list",
  globalSetup: "./e2e/setup.ts",
  use: { baseURL: "http://localhost:5174", launchOptions: { args: ["--autoplay-policy=no-user-gesture-required"] } },
  webServer: { command: "npx vite --port 5174 --strictPort", url: "http://localhost:5174", reuseExistingServer: true },
  projects: [
    { name: "telefono", testMatch: "responsive.spec.ts", use: { ...devices["Desktop Chrome"], viewport: { width: 390, height: 844 }, hasTouch: true } },
    { name: "escritorio", testMatch: "a11y.spec.ts", use: { ...devices["Desktop Chrome"], viewport: { width: 1280, height: 800 } } },
  ],
});
