import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { expect, test } from "vitest";
import { DedicationEditor } from "./DedicationEditor";

function Host({ initial = "" }: { initial?: string }) {
  const [value, setValue] = useState(initial);
  return <DedicationEditor value={value} onChange={setValue} />;
}

test("dedicatoria cuenta 140 caracteres", async () => {
  render(<Host />);
  expect(screen.getByText("Quedan 140 caracteres")).toBeInTheDocument();
  await userEvent.type(screen.getByRole("textbox"), "hola");
  expect(screen.getByText("Quedan 136 caracteres")).toBeInTheDocument();
});

test("no deja pasar de 140", async () => {
  render(<Host initial={"x".repeat(140)} />);
  await userEvent.type(screen.getByRole("textbox"), "y");
  expect(screen.getByRole("textbox")).toHaveValue("x".repeat(140));
  expect(screen.getByText("Quedan 0 caracteres")).toBeInTheDocument();
});
