import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test } from "vitest";
import type { TapeSummary } from "../api/types";
import { renderApp } from "../test-utils";
import { resetLibraryPrefs } from "./libraryPrefs";
import { TapePile } from "./TapePile";

const tape = (id: string, title: string): TapeSummary => ({
  id,
  title,
  color: "pink",
  is_creator: true,
  member_count: 2,
  track_count: 3,
  max_tracks: 12,
});

const tapes = [tape("t1", "Zeta"), tape("t2", "Alfa"), tape("t3", "Mitad")];

const order = () => screen.getAllByRole("link").map((link) => link.getAttribute("aria-label")!.split(",")[0]);

beforeEach(() => {
  localStorage.clear();
  resetLibraryPrefs();
});

test("los casetes salen en el orden que llega", () => {
  renderApp(<TapePile tapes={tapes} />);
  expect(order()).toEqual(["Zeta", "Alfa", "Mitad"]);
});

test("un casete fijado pasa al frente del montón", async () => {
  renderApp(<TapePile tapes={tapes} />);
  await userEvent.click(screen.getByRole("button", { name: "Fijar Mitad" }));
  expect(order()).toEqual(["Mitad", "Zeta", "Alfa"]);
  expect(screen.getByRole("button", { name: "Fijar Mitad" })).toHaveAttribute("aria-pressed", "true");
});

test("el montón respeta el orden por nombre", () => {
  localStorage.setItem("meloxo.library", JSON.stringify({ sort: "name", pinned: [] }));
  resetLibraryPrefs({ keepStorage: true });
  renderApp(<TapePile tapes={tapes} />);
  expect(order()).toEqual(["Alfa", "Mitad", "Zeta"]);
});
