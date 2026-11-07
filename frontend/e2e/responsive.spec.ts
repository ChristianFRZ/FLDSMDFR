import { expect, test } from "@playwright/test";
import { seriousProblems, signIn, state } from "./helpers";

async function noSideScroll(page: import("@playwright/test").Page, path: string) {
  await page.goto(path);
  await page.waitForLoadState("networkidle");
  // Una pantalla vacía tampoco desborda: sin esto, la prueba pasaría con la vista rota.
  await expect(page.locator("#content h1").first()).toBeVisible();
  const overflow = await page.evaluate(() => {
    const scrollers = [document.documentElement, ...document.querySelectorAll<HTMLElement>(".content")];
    return scrollers.map((element) => element.scrollWidth - element.clientWidth);
  });
  expect(Math.max(...overflow), `scroll horizontal en ${path}`).toBeLessThanOrEqual(0);
}

test("a 390 px hay pestañas abajo y reproductor compacto, sin scroll horizontal", async ({ page }) => {
  const { listener, tapeId, songTitle } = state();
  await signIn(page, listener);

  const home = await page.getByRole("link", { name: "Inicio", exact: true }).boundingBox();
  expect(home!.y).toBeGreaterThan(740);
  await expect(page.getByRole("link", { name: "Tu biblioteca" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Abrir reproductor" })).toBeVisible();
  await expect(page.getByRole("complementary", { name: "Sonando" })).toBeHidden();
  await expect(page.getByLabel("Volumen")).toBeHidden();

  const paths = ["/", `/search?q=${encodeURIComponent(songTitle)}`, "/library", "/stats", "/profile", `/tapes/${tapeId}`, "/tapes/new"];
  for (const path of paths) await noSideScroll(page, path);
});

test("a 390 px las vistas de Administrador no desbordan", async ({ page }) => {
  await signIn(page, state().admin);
  for (const path of ["/admin", "/admin/users", "/admin/requests", "/admin/catalog", "/admin/audit", "/admin/health"]) {
    await noSideScroll(page, path);
  }
});

test("a 390 px las vistas de Compositor no desbordan", async ({ page }) => {
  await signIn(page, state().composer);
  for (const path of ["/composer", "/composer/new", "/composer/albums", "/composer/profile", "/composer/stats"]) {
    await noSideScroll(page, path);
  }
});

test("a 390 px el Compositor lee sus títulos y edita una pista", async ({ page }) => {
  await signIn(page, state().composer);
  await page.goto("/composer");
  const title = page.locator(".song-text b").first();
  await expect(title).toBeVisible();
  const cut = await title.evaluate((element) => element.scrollWidth > element.clientWidth);
  expect(cut).toBe(false);
  await page.getByRole("link", { name: /^Editar / }).first().click();
  await expect(page.getByRole("heading", { name: "Editar pista" })).toBeVisible();
  await noSideScroll(page, new URL(page.url()).pathname);
});

test("a 390 px siguen disponibles aleatorio, repetir, favorita y cola", async ({ page }) => {
  const { listener, songTitle } = state();
  await signIn(page, listener);
  await page.goto(`/search?q=${encodeURIComponent(songTitle)}`);
  await page.getByRole("button", { name: `Reproducir ${songTitle}` }).first().click();
  await expect(page.getByRole("button", { name: "Pausar" })).toBeVisible();

  await page.getByRole("button", { name: "Abrir reproductor" }).click();
  const sheet = page.getByRole("dialog", { name: "Reproductor" });
  await expect(sheet.getByRole("heading", { name: songTitle })).toBeVisible();
  for (const name of ["Aleatorio", "Anterior", "Pausar", "Siguiente", /^Repetir/, /favoritas/, "Agregar a un casete o playlist"]) {
    await expect(sheet.getByRole("button", { name })).toBeVisible();
  }
  await expect(sheet.getByLabel("Posición en la pista")).toBeVisible();
  await expect(sheet.getByRole("region", { name: "Cola" })).toBeVisible();

  await sheet.getByRole("button", { name: "Aleatorio" }).click();
  await expect(sheet.getByRole("button", { name: "Aleatorio" })).toHaveAttribute("aria-pressed", "true");

  expect(await seriousProblems(page)).toEqual([]);

  await sheet.getByRole("button", { name: "Cerrar reproductor" }).click();
  await expect(sheet).toBeHidden();
  await expect(page.getByRole("button", { name: "Pausar" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Abrir reproductor" })).toBeFocused();
});

test("a 390 px el título de la pista del casete se puede leer", async ({ page }) => {
  const { listener, tapeId, songTitle } = state();
  await signIn(page, listener);
  await page.goto(`/tapes/${tapeId}`);
  const title = page.locator(".tracks .song-text b").first();
  await expect(title).toHaveText(songTitle);
  const clipped = await title.evaluate((element) => element.scrollWidth > element.clientWidth);
  expect(clipped).toBe(false);
});

test("a 320 px no hay scroll horizontal, como al acercar la página al 400 %", async ({ page }) => {
  const { admin } = state();
  await page.setViewportSize({ width: 320, height: 640 });
  await signIn(page, admin);
  for (const path of ["/", "/admin", "/admin/users", "/library"]) await noSideScroll(page, path);
});

test("axe no reporta fallas serias en el teléfono", async ({ page }) => {
  const { listener, tapeId } = state();
  await signIn(page, listener);
  await page.waitForLoadState("networkidle");
  expect(await seriousProblems(page)).toEqual([]);
  await page.goto(`/tapes/${tapeId}`);
  await expect(page.getByRole("heading", { name: "Casete e2e" })).toBeVisible();
  await page.waitForLoadState("networkidle");
  expect(await seriousProblems(page)).toEqual([]);
});

test("los controles táctiles miden al menos 44 px", async ({ page }) => {
  await signIn(page, state().listener);
  const targets = [
    page.getByRole("link", { name: "Inicio", exact: true }),
    page.getByRole("link", { name: "Tu biblioteca" }),
    page.getByRole("button", { name: "Abrir reproductor" }),
    page.getByRole("button", { name: "Atrás" }),
  ];
  for (const target of targets) {
    const box = await target.boundingBox();
    expect(Math.min(box!.width, box!.height)).toBeGreaterThanOrEqual(44);
  }
});

test("el casete se puede crear desde el teléfono", async ({ page }) => {
  await signIn(page, state().listener);
  await page.goto("/library");
  await page.getByRole("link", { name: "Crear casete" }).click();
  await expect(page).toHaveURL(/tapes\/new/);
});
