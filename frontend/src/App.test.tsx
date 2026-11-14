import { act, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { Shell } from "./App";
import { useAuth } from "./auth/AuthContext";
import { renderApp } from "./test-utils";

vi.mock("./auth/AuthContext", () => ({ useAuth: vi.fn() }));
vi.mock("./components/AddSong", () => ({ AddSongProvider: ({ children }: { children: unknown }) => children }));
vi.mock("./components/Sidebar", () => ({ Sidebar: () => null }));
vi.mock("./components/SearchBox", () => ({ SearchBox: () => null }));
vi.mock("./components/NoticesBell", () => ({ NoticesBell: () => null }));
vi.mock("./player/NowPanel", () => ({ NowPanel: () => null }));
vi.mock("./player/PlayerBar", () => ({ PlayerBar: () => null }));

const clearEntered = vi.fn();

function asAuth(entered: boolean) {
  vi.mocked(useAuth).mockReturnValue({
    user: { id: "u", display_name: "Ana", role: "listener" },
    entered,
    clearEntered,
  } as never);
  renderApp(<Shell />);
}

beforeEach(() => {
  vi.useFakeTimers();
  clearEntered.mockReset();
});

afterEach(() => {
  vi.useRealTimers();
});

test("muestra la animación de entrada cuando entered", () => {
  asAuth(true);
  expect(screen.getByRole("status", { name: "Entrando" })).toBeInTheDocument();
  act(() => vi.advanceTimersByTime(900));
  expect(clearEntered).toHaveBeenCalledTimes(1);
});

test("no la muestra si no", () => {
  asAuth(false);
  expect(screen.queryByRole("status", { name: "Entrando" })).not.toBeInTheDocument();
});
