import { mkdirSync, readdirSync, copyFileSync, rmSync } from "node:fs";
import { join, resolve } from "node:path";
// La spec vive fuera de frontend/: se importa el Playwright que ya está instalado allí.
import { expect, test, type APIRequestContext, type Page } from "../../../frontend/node_modules/@playwright/test";

const assets = resolve(__dirname, "../assets");
const EMAIL = "oyente00@demo.meloxo.dev";

async function signIn(page: Page) {
  const password = process.env.DEMO_PASSWORD;
  if (!password) throw new Error("Falta DEMO_PASSWORD en el entorno (carga el .env antes de correr).");
  await page.addInitScript(() => localStorage.setItem("meloxo.theme", "dark"));
  await page.goto("/login");
  await page.getByLabel("Correo").fill(EMAIL);
  await page.getByLabel("Contraseña").fill(password);
  await page.getByRole("button", { name: "Entrar" }).click();
  await expect(page.getByRole("heading", { name: "Tus casetes" })).toBeVisible();
  await page.waitForLoadState("networkidle");
}

/** Borra los casetes "Para el profe" de corridas anteriores para que cada corrida parta igual. */
async function limpiarCasetesDeLaDemo(request: APIRequestContext) {
  const login = await request.post("/api/auth/login", { data: { email: EMAIL, password: process.env.DEMO_PASSWORD } });
  const { access_token } = await login.json();
  const headers = { Authorization: `Bearer ${access_token}` };
  const tapes = (await (await request.get("/api/tapes", { headers })).json()) as { id: string; title: string }[];
  for (const tape of tapes.filter((t) => t.title === "Para el profe")) {
    await request.delete(`/api/tapes/${tape.id}`, { headers });
  }
}

test.beforeAll(async ({ playwright }) => {
  const request = await playwright.request.newContext({ baseURL: "http://localhost:8080" });
  await limpiarCasetesDeLaDemo(request);
  await request.dispose();
});

test.describe("capturas", () => {
  test.use({ viewport: { width: 1600, height: 900 }, deviceScaleFactor: 2 });

  test("inicio, casete y reproductor", async ({ page }) => {
    await signIn(page);
    await page.waitForTimeout(2500); // portadas y caída de los casetes
    await page.screenshot({ path: join(assets, "cap-inicio.png") });

    // Un casete que traiga dedicatorias.
    const tapes = page.locator('a[aria-label$="pistas"]');
    const total = await tapes.count();
    let found = false;
    for (let i = 0; i < Math.min(total, 12) && !found; i += 1) {
      await page.goto("/");
      await page.locator('a[aria-label$="pistas"]').nth(i).click();
      await expect(page.locator("h1.page-title")).toBeVisible();
      await page.waitForLoadState("networkidle");
      found = (await page.locator(".tape-page").getByText(/de .+/).count()) > 0 && (await page.locator(".note, [class*=dedic]").count()) > 0;
    }
    await page.waitForTimeout(1500);
    await page.screenshot({ path: join(assets, "cap-casete.png") });

    await page.getByRole("button", { name: "Reproducir", exact: true }).first().click();
    await expect(page.getByRole("button", { name: "Pausar" })).toBeVisible();
    await page.waitForTimeout(6000);
    await page.screenshot({ path: join(assets, "cap-reproductor.png") });
  });
});

test.describe("video", () => {
  test("demo: crear casete, dos pistas, dedicatoria y reproducir", async ({ browser }) => {
    // El inicio de sesión se hace aparte para que el video no grabe el correo ni la contraseña.
    const auth = await browser.newContext({ viewport: { width: 1280, height: 720 }, colorScheme: "dark" });
    await signIn(await auth.newPage());
    const storageState = await auth.storageState();
    await auth.close();

    const dir = resolve(__dirname, ".results/video");
    rmSync(dir, { recursive: true, force: true });
    const context = await browser.newContext({
      storageState,
      colorScheme: "dark",
      viewport: { width: 1280, height: 720 },
      recordVideo: { dir, size: { width: 1280, height: 720 } },
    });
    const page = await context.newPage();
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Tus casetes" })).toBeVisible();
    await page.waitForTimeout(2500);

    await page.goto("/tapes/new");
    await page.getByLabel("Nombre").pressSequentially("Para el profe", { delay: 90 });
    await page.waitForTimeout(800);
    await page.getByRole("button", { name: "Crear casete" }).click();
    await expect(page.locator("h1.page-title")).toHaveText("Para el profe", { timeout: 10_000 });
    await page.waitForTimeout(1200);

    const dedicatorias = ["para que el semestre termine con buena música", "gracias por las clases"];
    const busquedas = ["rock", "jazz"];
    for (let i = 0; i < 2; i += 1) {
      const toggle = page.getByRole("button", { name: "Agregar pista" });
      if ((await toggle.getAttribute("aria-expanded")) !== "true") await toggle.click();
      await page.getByRole("searchbox", { name: "Buscar pista para el casete" }).pressSequentially(busquedas[i], { delay: 80 });
      const first = page.locator(".add-track .pick-list button").first();
      await first.waitFor({ timeout: 10_000 });
      await first.click();
      await page.getByRole("textbox", { name: /Dedicatoria/ }).pressSequentially(dedicatorias[i], { delay: 35 });
      await page.waitForTimeout(500);
      await page.getByRole("button", { name: "Agregar al casete" }).click();
      await expect(page.getByText(`${i + 1} de`).first()).toBeVisible({ timeout: 10_000 });
      await page.waitForTimeout(1200);
    }

    await page.getByRole("button", { name: "Reproducir", exact: true }).first().click();
    await expect(page.getByRole("button", { name: "Pausar" })).toBeVisible();
    await page.waitForTimeout(8000);

    const video = page.video();
    await context.close();
    mkdirSync(assets, { recursive: true });
    const webm = readdirSync(dir).find((f) => f.endsWith(".webm"));
    if (!webm || !video) throw new Error("No se grabó el video");
    copyFileSync(join(dir, webm), join(assets, "demo.webm"));
  });
});
