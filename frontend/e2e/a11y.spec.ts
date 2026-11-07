import { expect, test } from "@playwright/test";
import { seriousProblems, signIn, state, tabTo } from "./helpers";

test("flujo solo con teclado: buscar, reproducir, pausar", async ({ page }) => {
  const { listener, songTitle } = state();
  await signIn(page, listener);

  await tabTo(page, page.getByRole("searchbox", { name: "Buscar canciones o artistas" }));
  await page.keyboard.type(songTitle);
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/search/);

  const play = page.getByRole("button", { name: `Reproducir ${songTitle}` }).first();
  await expect(play).toBeVisible();
  await tabTo(page, play);
  await page.keyboard.press("Enter");

  const pause = page.getByRole("button", { name: "Pausar" });
  await expect(pause).toBeVisible();
  await tabTo(page, pause);
  await page.keyboard.press("Enter");
  await expect(page.getByRole("button", { name: "Reproducir", exact: true })).toBeVisible();
});

test("foco visible en todos los controles", async ({ page }) => {
  await signIn(page, state().listener);
  const missing = new Set<string>();
  for (let step = 0; step < 40; step += 1) {
    await page.keyboard.press("Tab");
    const problem = await page.evaluate(() => {
      const active = document.activeElement as HTMLElement | null;
      if (!active || active === document.body) return null;
      const visible = (element: Element) => {
        const style = getComputedStyle(element);
        return style.outlineStyle !== "none" && parseFloat(style.outlineWidth) >= 2;
      };
      const wrapper = active.closest(".search");
      if (visible(active) || (wrapper && visible(wrapper))) return null;
      return active.getAttribute("aria-label") ?? active.textContent?.trim().slice(0, 40) ?? active.tagName;
    });
    if (problem) missing.add(problem);
  }
  expect([...missing]).toEqual([]);
});

test("axe no reporta fallas serias en Inicio", async ({ page }) => {
  await signIn(page, state().listener);
  await page.waitForLoadState("networkidle");
  expect(await seriousProblems(page)).toEqual([]);
});

test("axe no reporta fallas serias en Casete", async ({ page }) => {
  const { listener, tapeId } = state();
  await signIn(page, listener);
  await page.goto(`/tapes/${tapeId}`);
  await expect(page.getByRole("heading", { name: "Casete e2e" })).toBeVisible();
  await page.waitForLoadState("networkidle");
  expect(await seriousProblems(page)).toEqual([]);
});

test("axe no reporta fallas serias en Panel", async ({ page }) => {
  await signIn(page, state().admin);
  await page.goto("/admin");
  await expect(page.getByRole("heading", { name: "Administración" })).toBeVisible();
  await expect(page.getByRole("list", { name: "Salud del sistema" })).toContainText("Base de datos");
  await page.waitForLoadState("networkidle");
  expect(await seriousProblems(page)).toEqual([]);
});
