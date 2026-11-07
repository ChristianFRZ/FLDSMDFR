import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import { Note } from "./Note";
import { Tape } from "./Tape";

test("la nota muestra su contenido", () => {
  render(<Note>Para ti</Note>);
  expect(screen.getByText("Para ti")).toBeInTheDocument();
});

test("la nota lleva cinta solo si se pide", () => {
  const { container, rerender } = render(<Note>x</Note>);
  expect(container.firstChild).not.toHaveClass("note-taped");
  rerender(<Note tape>x</Note>);
  expect(container.firstChild).toHaveClass("note-taped");
});

test("el casete expone su título y color", () => {
  const { container } = render(<Tape title="Viaje" color="teal" />);
  expect(screen.getByText("Viaje")).toBeInTheDocument();
  expect(container.firstChild).toHaveStyle({ "--shell": "#00d1be" });
});
