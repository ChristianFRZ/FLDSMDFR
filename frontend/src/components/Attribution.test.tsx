import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import { song } from "../test-utils";
import { Attribution } from "./Attribution";

test("Attribution de Jamendo muestra artista y enlace a la pista, sin licencia", () => {
  render(
    <Attribution
      song={song({
        source: "jamendo",
        jamendo_url: "https://www.jamendo.com/track/1",
        license: "CC BY-NC-SA",
        license_url: "https://creativecommons.org/licenses/by-nc-sa/3.0/",
      })}
    />,
  );
  expect(screen.getByText(/Marea Baja · vía/)).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Jamendo" })).toHaveAttribute("href", "https://www.jamendo.com/track/1");
  expect(screen.queryByText(/CC BY/)).not.toBeInTheDocument();
});

test("Attribution local muestra artista y MELOXO, sin licencia", () => {
  render(<Attribution song={song()} />);
  expect(screen.getByText("Marea Baja · vía MELOXO")).toBeInTheDocument();
  expect(screen.queryByText(/CC BY/)).not.toBeInTheDocument();
});
