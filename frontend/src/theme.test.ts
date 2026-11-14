import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { resetTheme, resolveTheme, useTheme } from "./theme";

const KEY = "meloxo.theme";

function stubSystem(light: boolean) {
  const listeners = new Set<() => void>();
  const media = {
    matches: light,
    addEventListener: (_: string, listener: () => void) => listeners.add(listener),
    removeEventListener: (_: string, listener: () => void) => listeners.delete(listener),
  };
  vi.stubGlobal("matchMedia", vi.fn(() => media));
  return {
    change(next: boolean) {
      media.matches = next;
      listeners.forEach((listener) => listener());
    },
  };
}

const attribute = () => document.documentElement.getAttribute("data-theme");
const meta = (name: string) => document.querySelector(`meta[name="${name}"]`)?.getAttribute("content");

beforeEach(() => {
  localStorage.clear();
  document.head.innerHTML = '<meta name="theme-color" content="#141317"><meta name="color-scheme" content="dark">';
  document.documentElement.removeAttribute("data-theme");
  stubSystem(false);
  resetTheme();
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

test("sin nada guardado, el tema es oscuro como siempre", () => {
  const { result } = renderHook(() => useTheme());
  expect(result.current.pref).toBe("dark");
  expect(result.current.resolved).toBe("dark");
  expect(attribute()).toBe("dark");
});

test("resolveTheme decide por la preferencia y, si es sistema, por el equipo", () => {
  expect(resolveTheme("dark", true)).toBe("dark");
  expect(resolveTheme("light", false)).toBe("light");
  expect(resolveTheme("system", true)).toBe("light");
  expect(resolveTheme("system", false)).toBe("dark");
});

test("elegir claro lo aplica, lo guarda y cambia los colores del navegador", () => {
  const { result } = renderHook(() => useTheme());
  act(() => result.current.setPref("light"));
  expect(result.current.resolved).toBe("light");
  expect(attribute()).toBe("light");
  expect(localStorage.getItem(KEY)).toBe("light");
  expect(meta("theme-color")).toBe("#ebe5d8");
  expect(meta("color-scheme")).toBe("light");
});

test("volver a oscuro restaura los colores del navegador", () => {
  const { result } = renderHook(() => useTheme());
  act(() => result.current.setPref("light"));
  act(() => result.current.setPref("dark"));
  expect(meta("theme-color")).toBe("#141317");
  expect(meta("color-scheme")).toBe("dark");
});

test("se recuerda al recargar", () => {
  localStorage.setItem(KEY, "light");
  resetTheme();
  const { result } = renderHook(() => useTheme());
  expect(result.current.pref).toBe("light");
  expect(attribute()).toBe("light");
});

test("un valor guardado que no sirve se trata como ausente", () => {
  localStorage.setItem(KEY, "morado");
  resetTheme();
  const { result } = renderHook(() => useTheme());
  expect(result.current.pref).toBe("dark");
});

test("con sistema, sigue al equipo y reacciona cuando este cambia", () => {
  const system = stubSystem(false);
  localStorage.setItem(KEY, "system");
  resetTheme();
  const { result } = renderHook(() => useTheme());
  expect(result.current.resolved).toBe("dark");
  act(() => system.change(true));
  expect(result.current.resolved).toBe("light");
  expect(attribute()).toBe("light");
});

test("oscuro explícito ignora que el equipo esté en claro", () => {
  const system = stubSystem(true);
  localStorage.setItem(KEY, "dark");
  resetTheme();
  const { result } = renderHook(() => useTheme());
  act(() => system.change(true));
  expect(result.current.resolved).toBe("dark");
});

test("si el navegador no deja guardar, el cambio vale en esta sesión", () => {
  vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
    throw new DOMException("lleno", "QuotaExceededError");
  });
  const { result } = renderHook(() => useTheme());
  act(() => result.current.setPref("light"));
  expect(result.current.resolved).toBe("light");
  expect(attribute()).toBe("light");
});

test("sin matchMedia (entornos viejos) usa oscuro", () => {
  vi.stubGlobal("matchMedia", undefined);
  localStorage.setItem(KEY, "system");
  resetTheme();
  const { result } = renderHook(() => useTheme());
  expect(result.current.resolved).toBe("dark");
});
