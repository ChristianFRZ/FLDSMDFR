import { fireEvent, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";
import { api } from "../api/client";
import { TAPE_COLORS } from "../components/tapeColors";
import { renderApp } from "../test-utils";
import { TapeCreate } from "./TapeCreate";

vi.mock("../api/client", async (original) => ({
  ...(await original<typeof import("../api/client")>()),
  api: vi.fn(),
}));

beforeEach(() => {
  vi.mocked(api).mockReset();
  vi.mocked(api).mockResolvedValue({ id: "t1" });
});

async function create() {
  await userEvent.type(screen.getByLabelText("Nombre"), "Para el viaje");
  await userEvent.click(screen.getByRole("button", { name: "Crear casete" }));
  await waitFor(() => expect(api).toHaveBeenCalled());
  return vi.mocked(api).mock.calls[0][1]?.json;
}

test("ofrece los doce colores del estante", () => {
  renderApp(<TapeCreate />);
  expect(TAPE_COLORS).toHaveLength(12);
  expect(screen.getAllByRole("radio")).toHaveLength(12);
  expect(screen.getByRole("radio", { name: "Rosa" })).toBeChecked();
});

test("crea el casete con el color elegido del estante", async () => {
  renderApp(<TapeCreate />);
  await userEvent.click(screen.getByRole("radio", { name: "Lima" }));
  expect(await create()).toEqual({ title: "Para el viaje", color: "#b6e03c" });
});

test("el color libre reemplaza la elección del estante", async () => {
  renderApp(<TapeCreate />);
  fireEvent.input(screen.getByLabelText("Color libre"), { target: { value: "#123456" } });
  expect(screen.getByRole("radio", { name: "Rosa" })).not.toBeChecked();
  expect(await create()).toEqual({ title: "Para el viaje", color: "#123456" });
});
