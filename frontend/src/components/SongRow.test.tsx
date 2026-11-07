import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, test, vi } from "vitest";
import { renderApp, song } from "../test-utils";
import { SongRow } from "./SongRow";

vi.mock("./AddSong", () => ({ useAddSong: () => vi.fn() }));

test("reproduce al pulsar", async () => {
  const onPlay = vi.fn();
  renderApp(<SongRow song={song()} onPlay={onPlay} />);
  await userEvent.click(screen.getByRole("button", { name: "Reproducir Luz de carretera" }));
  expect(onPlay).toHaveBeenCalledOnce();
});

test("pista no disponible aparece marcada y no se puede reproducir", () => {
  renderApp(<SongRow song={song({ available: false })} onPlay={vi.fn()} />);
  expect(screen.getByText("No disponible")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Reproducir Luz de carretera" })).toBeDisabled();
});
