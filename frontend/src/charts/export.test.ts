import type { Chart } from "chart.js";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { download } from "../api/client";
import { exportCsv, exportPng } from "./export";

vi.mock("../api/client", async (original) => ({
  ...(await original<typeof import("../api/client")>()),
  download: vi.fn(),
}));

let saved: { href: string; name: string }[];

beforeEach(() => {
  saved = [];
  vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (this: HTMLAnchorElement) {
    saved.push({ href: this.href, name: this.download });
  });
  URL.createObjectURL = vi.fn(() => "blob:csv");
  URL.revokeObjectURL = vi.fn();
});

afterEach(() => {
  vi.restoreAllMocks();
});

test("exportPng genera image/png con el nombre del reporte", () => {
  const toBase64Image = vi.fn(() => "data:image/png;base64,AAAA");
  exportPng({ toBase64Image } as unknown as Chart, "genres");
  expect(toBase64Image).toHaveBeenCalledWith("image/png", 1);
  expect(saved).toEqual([{ href: "data:image/png;base64,AAAA", name: "meloxo-genres.png" }]);
});

test("exportCsv pide el CSV al backend con sesión y lo guarda", async () => {
  vi.mocked(download).mockResolvedValue(new Blob(["a,b"], { type: "text/csv" }));
  await exportCsv("genres");
  expect(download).toHaveBeenCalledWith(expect.stringMatching(/^\/api\/admin\/reports\/genres\.csv\?tz=/));
  expect(saved).toEqual([{ href: "blob:csv", name: "meloxo-genres.csv" }]);
});
