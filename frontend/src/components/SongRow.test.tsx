import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";
import { renderApp, song } from "../test-utils";
import { SongRow } from "./SongRow";

const player = vi.hoisted(() => ({ playNext: vi.fn(), addToQueue: vi.fn() }));

vi.mock("./AddSong", () => ({ useAddSong: () => vi.fn() }));
vi.mock("../player/PlayerProvider", () => ({ usePlayer: () => player }));

beforeEach(() => {
  player.playNext.mockReset();
  player.addToQueue.mockReset();
});

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

test("una pista no disponible no ofrece acciones de cola", () => {
  renderApp(<SongRow song={song({ available: false })} onPlay={vi.fn()} />);
  expect(screen.queryByRole("button", { name: /Más acciones/ })).not.toBeInTheDocument();
});

test("el menú ofrece reproducir siguiente", async () => {
  const chosen = song();
  renderApp(<SongRow song={chosen} onPlay={vi.fn()} />);
  await userEvent.click(screen.getByRole("button", { name: "Más acciones de Luz de carretera" }));
  await userEvent.click(screen.getByRole("button", { name: "Reproducir siguiente" }));
  expect(player.playNext).toHaveBeenCalledWith(chosen);
  expect(screen.queryByRole("button", { name: "Reproducir siguiente" })).not.toBeInTheDocument();
});

test("el menú ofrece agregar a la cola", async () => {
  const chosen = song();
  renderApp(<SongRow song={chosen} onPlay={vi.fn()} />);
  await userEvent.click(screen.getByRole("button", { name: "Más acciones de Luz de carretera" }));
  await userEvent.click(screen.getByRole("button", { name: "Agregar a la cola" }));
  expect(player.addToQueue).toHaveBeenCalledWith(chosen);
});

test("Escape cierra el menú y devuelve el foco al botón", async () => {
  renderApp(<SongRow song={song()} onPlay={vi.fn()} />);
  const opener = screen.getByRole("button", { name: "Más acciones de Luz de carretera" });
  await userEvent.click(opener);
  expect(opener).toHaveAttribute("aria-expanded", "true");
  await userEvent.keyboard("{Escape}");
  expect(screen.queryByRole("button", { name: "Agregar a la cola" })).not.toBeInTheDocument();
  expect(opener).toHaveFocus();
});
