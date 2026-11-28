import { act, render, screen } from "@testing-library/react";
import { beforeEach, expect, test } from "vitest";
import horizontalLight from "../assets/meloxo-horizontal-color-light.svg";
import stackedDark from "../assets/meloxo-stacked-color-dark.svg";
import stackedLight from "../assets/meloxo-stacked-color-light.svg";
import { resetTheme, useTheme } from "../theme";
import { Logo } from "./Logo";

beforeEach(() => {
  localStorage.clear();
  act(() => resetTheme());
});

function Switch() {
  const { setPref } = useTheme();
  return <button type="button" onClick={() => setPref("light")}>Claro</button>;
}

test("en oscuro usa el logo para fondo oscuro", () => {
  render(<Logo variant="stacked" alt="MELOXO" />);
  expect(screen.getByAltText("MELOXO").getAttribute("src")).toBe(stackedDark);
});

test("en claro usa el logo para fondo claro", () => {
  localStorage.setItem("meloxo.theme", "light");
  act(() => resetTheme());
  render(<Logo variant="horizontal" alt="" className="brand" />);
  const image = document.querySelector("img.brand")!;
  expect(image.getAttribute("src")).toBe(horizontalLight);
});

test("cambia solo cuando cambia el tema", () => {
  render(<><Logo variant="stacked" alt="MELOXO" /><Switch /></>);
  expect(screen.getByAltText("MELOXO").getAttribute("src")).toBe(stackedDark);
  act(() => screen.getByRole("button", { name: "Claro" }).click());
  expect(screen.getByAltText("MELOXO").getAttribute("src")).toBe(stackedLight);
  expect(stackedLight).not.toBe(stackedDark);
});
