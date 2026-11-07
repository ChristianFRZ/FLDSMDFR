import { act, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { api } from "../api/client";
import { renderApp } from "../test-utils";
import { NoticesBell } from "./NoticesBell";

vi.mock("../api/client", async (original) => ({
  ...(await original<typeof import("../api/client")>()),
  api: vi.fn(),
}));

beforeEach(() => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  vi.mocked(api).mockResolvedValue({ unread: 2, items: [], degraded: false });
});

afterEach(() => {
  vi.useRealTimers();
  vi.clearAllMocks();
});

test("avisos consultan cada 30 s", async () => {
  renderApp(<NoticesBell />);
  await act(() => vi.advanceTimersByTimeAsync(100));
  expect(api).toHaveBeenCalledTimes(1);
  await act(() => vi.advanceTimersByTimeAsync(29_000));
  expect(api).toHaveBeenCalledTimes(1);
  await act(() => vi.advanceTimersByTimeAsync(1_500));
  expect(api).toHaveBeenCalledTimes(2);
});

test("muestra cuántos avisos hay sin leer", async () => {
  renderApp(<NoticesBell />);
  await act(() => vi.advanceTimersByTimeAsync(100));
  expect(screen.getByRole("button", { name: "Avisos, 2 sin leer" })).toBeInTheDocument();
});
