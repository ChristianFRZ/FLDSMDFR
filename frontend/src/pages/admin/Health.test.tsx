import { screen, within } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import { api } from "../../api/client";
import { renderApp, routes } from "../../test-utils";
import { Health } from "./Health";

vi.mock("../../api/client", async (original) => ({
  ...(await original<typeof import("../../api/client")>()),
  api: vi.fn(),
}));
vi.mock("../../charts/ChartCanvas", () => ({ ChartCanvas: () => <div data-testid="chart" /> }));

const answers = {
  "/api/admin/health": {
    services: [
      { name: "app", status: "up", uptime_seconds: 7200 },
      { name: "database", status: "up", ms: 4 },
      { name: "jamendo", status: "not_configured" },
      { name: "aggregates", status: "delayed", lag_seconds: 360 },
    ],
  },
  "/api/metrics/latency": {
    items: [
      { minute: new Date().toISOString(), module: "catalog", count: 10, errors: 2, p50_ms: 8, p95_ms: 38 },
      { minute: new Date().toISOString(), module: "streaming", count: 4, errors: 0, p50_ms: 80, p95_ms: 184 },
    ],
  },
  "/api/admin/health/system": {
    disk: { used_bytes: 2 * 1024 ** 3, total_bytes: 40 * 1024 ** 3 },
    database: { size_bytes: 186 * 1024 ** 2, connections: 12, max_connections: 100 },
    system: { version: "01-monolito", started_at: "2026-11-07T10:00:00Z", python: "3.12.1", postgres: "16.4" },
  },
  "/api/admin/health/activity": { minutes: 30, listeners: 14, plays: 38 },
};

beforeEach(() => {
  vi.mocked(api).mockReset();
  vi.mocked(api).mockImplementation(routes(answers) as typeof api);
});

test("resume el peor estado y da detalle de cada servicio", async () => {
  renderApp(<Health />);
  expect(await screen.findByText("1 servicio con retraso")).toBeInTheDocument();
  expect(screen.getByText("En línea · activa hace 2 h")).toBeInTheDocument();
  expect(screen.getByText("En línea · responde en 4 ms")).toBeInTheDocument();
  expect(screen.getByText("Con retraso · 6 min sin actualizar")).toBeInTheDocument();
  expect(screen.getByText("Sin configurar")).toBeInTheDocument();
});

test("una integración sin configurar no cuenta como problema", async () => {
  vi.mocked(api).mockImplementation(
    routes({ ...answers, "/api/admin/health": { services: [{ name: "app", status: "up" }, { name: "jamendo", status: "not_configured" }] } }) as typeof api,
  );
  renderApp(<Health />);
  expect(await screen.findByText("Todo en orden")).toBeInTheDocument();
});

test("muestra cada módulo con peticiones, p95 y errores", async () => {
  renderApp(<Health />);
  const table = await screen.findByRole("table", { name: "Módulos" });
  const [, first, second] = within(table).getAllByRole("row");
  expect(within(first).getAllByRole("cell").map((cell) => cell.textContent)).toEqual(["Catálogo", "10", "38 ms", "2"]);
  expect(within(second).getAllByRole("cell").map((cell) => cell.textContent)).toEqual(["Streaming", "4", "184 ms", "0"]);
});

test("muestra recursos, actividad y datos del sistema", async () => {
  renderApp(<Health />);
  expect(await screen.findByText("2 GB de 40 GB")).toBeInTheDocument();
  expect(screen.getByText("186 MB")).toBeInTheDocument();
  expect(screen.getByText("12 de 100")).toBeInTheDocument();
  expect(screen.getByText("01-monolito")).toBeInTheDocument();
  expect(screen.getByText("16.4")).toBeInTheDocument();
  expect(await screen.findByText("Oyentes")).toBeInTheDocument();
  expect(screen.getByText(/Últimos 30 minutos · actualizado a las/)).toBeInTheDocument();
  expect(screen.getByTestId("chart")).toBeInTheDocument();
});
