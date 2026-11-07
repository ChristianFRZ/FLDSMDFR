import type { Chart } from "chart.js";
import { download } from "../api/client";

function save(href: string, name: string) {
  const link = document.createElement("a");
  link.href = href;
  link.download = name;
  link.click();
}

export function exportPng(chart: Chart, name: string) {
  save(chart.toBase64Image("image/png", 1), `meloxo-${name}.png`);
}

export async function exportCsv(name: string) {
  const zone = Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
  const url = URL.createObjectURL(await download(`/api/admin/reports/${name}.csv?tz=${encodeURIComponent(zone)}`));
  save(url, `meloxo-${name}.csv`);
  URL.revokeObjectURL(url);
}
