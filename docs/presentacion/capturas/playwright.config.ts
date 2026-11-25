// Configuración propia de las capturas: no toca la de frontend/. Ver README.md.
export default {
  testDir: ".",
  testMatch: "capturar.spec.ts",
  outputDir: "./.results",
  workers: 1,
  fullyParallel: false,
  timeout: 120_000,
  reporter: "list",
  use: {
    baseURL: "http://localhost:8080",
    colorScheme: "dark",
    launchOptions: { args: ["--autoplay-policy=no-user-gesture-required"] },
  },
};
