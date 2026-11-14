import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { LogoAnimation } from "./LogoAnimation";

const originalMatchMedia = window.matchMedia;

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
  window.matchMedia = originalMatchMedia;
});

test("intro llama onDone tras 1200 ms y no antes", () => {
  const onDone = vi.fn();
  render(<LogoAnimation variant="intro" onDone={onDone} />);
  act(() => vi.advanceTimersByTime(1199));
  expect(onDone).toHaveBeenCalledTimes(0);
  act(() => vi.advanceTimersByTime(1));
  expect(onDone).toHaveBeenCalledTimes(1);
});

test("enter llama onDone tras 900 ms", () => {
  const onDone = vi.fn();
  render(<LogoAnimation variant="enter" onDone={onDone} />);
  act(() => vi.advanceTimersByTime(899));
  expect(onDone).toHaveBeenCalledTimes(0);
  act(() => vi.advanceTimersByTime(1));
  expect(onDone).toHaveBeenCalledTimes(1);
});

test("un clic salta y onDone se llama solo una vez", () => {
  const onDone = vi.fn();
  render(<LogoAnimation variant="intro" onDone={onDone} />);
  fireEvent.click(screen.getByRole("status"));
  expect(onDone).toHaveBeenCalledTimes(1);
  act(() => vi.advanceTimersByTime(2000));
  expect(onDone).toHaveBeenCalledTimes(1);
});

test("cualquier tecla salta la animación", () => {
  const onDone = vi.fn();
  render(<LogoAnimation variant="enter" onDone={onDone} />);
  fireEvent.keyDown(window, { key: "Escape" });
  expect(onDone).toHaveBeenCalledTimes(1);
  act(() => vi.advanceTimersByTime(2000));
  expect(onDone).toHaveBeenCalledTimes(1);
});

test("con reduced-motion llama onDone de inmediato", () => {
  window.matchMedia = vi.fn((query: string) => ({
    matches: query === "(prefers-reduced-motion: reduce)",
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })) as unknown as typeof window.matchMedia;
  const onDone = vi.fn();
  render(<LogoAnimation variant="intro" onDone={onDone} />);
  act(() => vi.advanceTimersByTime(0));
  expect(onDone).toHaveBeenCalledTimes(1);
});

test("expone el estado accesible", () => {
  render(<LogoAnimation variant="intro" onDone={() => {}} />);
  const status = screen.getByRole("status", { name: "Cargando MELOXO" });
  expect(status).toHaveClass("logo-anim", "logo-anim-intro");
});

test("enter se anuncia como Entrando y solo muestra el símbolo", () => {
  render(<LogoAnimation variant="enter" onDone={() => {}} />);
  const status = screen.getByRole("status", { name: "Entrando" });
  expect(status).toHaveClass("logo-anim", "logo-anim-enter");
  expect(status.querySelector(".logo-anim-wordmark")).toBeNull();
  expect(status.querySelector(".logo-anim-symbol")).not.toBeNull();
});

test("desmontar antes de tiempo no llama onDone", () => {
  const onDone = vi.fn();
  const { unmount } = render(<LogoAnimation variant="intro" onDone={onDone} />);
  unmount();
  act(() => vi.advanceTimersByTime(2000));
  expect(onDone).not.toHaveBeenCalled();
});
