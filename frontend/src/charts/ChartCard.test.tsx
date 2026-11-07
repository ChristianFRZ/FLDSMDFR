import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";
import { api, ApiError } from "../api/client";
import { renderApp } from "../test-utils";
import { ChartCard } from "./ChartCard";

vi.mock("../api/client", async (original) => ({
  ...(await original<typeof import("../api/client")>()),
  api: vi.fn(),
}));
vi.mock("./ChartCanvas", () => ({ ChartCanvas: () => <div data-testid="chart" /> }));

const columns = [{ key: "genre", label: "Género" }, { key: "plays", label: "Reproducciones" }];
const props = {
  title: "Géneros",
  url: "/api/metrics/genres",
  columns,
  chart: () => ({ type: "bar" as const, data: { labels: [], datasets: [] } }),
};

beforeEach(() => {
  vi.mocked(api).mockReset();
});

test("ChartCard con error muestra aviso y el resto sigue", async () => {
  vi.mocked(api).mockRejectedValue(new ApiError(503, "x", "x"));
  renderApp(
    <>
      <ChartCard {...props} />
      <p>El resto de la página</p>
    </>,
  );
  expect(await screen.findByText("Datos no disponibles por ahora")).toBeInTheDocument();
  expect(screen.getByText("El resto de la página")).toBeInTheDocument();
});

test("ChartCard sin datos muestra estado vacío", async () => {
  vi.mocked(api).mockResolvedValue({ items: [] });
  renderApp(<ChartCard {...props} />);
  expect(await screen.findByText("Aún no hay datos")).toBeInTheDocument();
  expect(screen.queryByTestId("chart")).not.toBeInTheDocument();
});

test("con datos dibuja la gráfica y ofrece una tabla accesible", async () => {
  vi.mocked(api).mockResolvedValue({ items: [{ genre: "rock", plays: 3 }] });
  renderApp(<ChartCard {...props} />);
  expect(await screen.findByTestId("chart")).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Ver tabla de Géneros" }));
  expect(screen.getByRole("table", { name: "Géneros" })).toBeInTheDocument();
  expect(screen.getByRole("cell", { name: "rock" })).toBeInTheDocument();
});
