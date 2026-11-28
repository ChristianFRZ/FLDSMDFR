import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { resetLibraryPrefs, useLibraryPrefs } from "./libraryPrefs";

const KEY = "meloxo.library";

beforeEach(() => {
  localStorage.clear();
  resetLibraryPrefs();
});

afterEach(() => {
  vi.restoreAllMocks();
});

test("empieza sin fijadas y con el orden predeterminado", () => {
  const { result } = renderHook(() => useLibraryPrefs());
  expect(result.current.pinned).toEqual([]);
  expect(result.current.sort).toBe("default");
});

test("fijar y soltar", () => {
  const { result } = renderHook(() => useLibraryPrefs());
  act(() => result.current.togglePin("a"));
  act(() => result.current.togglePin("b"));
  expect(result.current.pinned).toEqual(["a", "b"]);
  act(() => result.current.togglePin("a"));
  expect(result.current.pinned).toEqual(["b"]);
});

test("cambiar el orden", () => {
  const { result } = renderHook(() => useLibraryPrefs());
  act(() => result.current.setSort("name"));
  expect(result.current.sort).toBe("name");
});

test("dos lugares de la pantalla ven el mismo cambio", () => {
  const side = renderHook(() => useLibraryPrefs());
  const page = renderHook(() => useLibraryPrefs());
  act(() => side.result.current.togglePin("a"));
  expect(page.result.current.pinned).toEqual(["a"]);
});

test("se recuerda al recargar", () => {
  const first = renderHook(() => useLibraryPrefs());
  act(() => first.result.current.togglePin("a"));
  act(() => first.result.current.setSort("name"));
  first.unmount();
  resetLibraryPrefs({ keepStorage: true });
  const second = renderHook(() => useLibraryPrefs());
  expect(second.result.current.pinned).toEqual(["a"]);
  expect(second.result.current.sort).toBe("name");
});

test("un valor guardado que no sirve se trata como ausente", () => {
  localStorage.setItem(KEY, "{no es json");
  resetLibraryPrefs({ keepStorage: true });
  const { result } = renderHook(() => useLibraryPrefs());
  expect(result.current.pinned).toEqual([]);
  expect(result.current.sort).toBe("default");
});

test("un orden desconocido y fijadas que no son texto se descartan", () => {
  localStorage.setItem(KEY, JSON.stringify({ sort: "raro", pinned: ["a", 7, null, "b"] }));
  resetLibraryPrefs({ keepStorage: true });
  const { result } = renderHook(() => useLibraryPrefs());
  expect(result.current.sort).toBe("default");
  expect(result.current.pinned).toEqual(["a", "b"]);
});

test("si el navegador no deja guardar, igual funciona en esta sesión", () => {
  vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
    throw new DOMException("lleno", "QuotaExceededError");
  });
  const { result } = renderHook(() => useLibraryPrefs());
  act(() => result.current.togglePin("a"));
  expect(result.current.pinned).toEqual(["a"]);
});
