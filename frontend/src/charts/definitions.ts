import type { ChartConfiguration, ChartOptions, Scale, ScriptableContext, TooltipItem } from "chart.js";
import { barStyle, baseOptions, GRID, lineStyle, noGridX, SERIES, SURFACE } from "./index";
import type { Column, Row } from "./ChartCard";

const dayFormat = new Intl.DateTimeFormat("es", { day: "numeric", month: "short" });
const hourFormat = new Intl.DateTimeFormat("es", { hour: "2-digit", minute: "2-digit" });

/** `bucket` llega sin zona porque ya viene en la del navegador. */
export const formatDay = (value: string) => dayFormat.format(new Date(`${value.slice(0, 10)}T00:00:00`));
export const formatMinute = (value: string) => hourFormat.format(new Date(value));
export const formatHour = (value: string) => `${formatDay(value)} ${value.slice(11, 13)}:00`;

export const browserZone = () => Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";

const pad = (value: number) => String(value).padStart(2, "0");
const localDay = (date: Date) => `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T00:00:00`;

/** El backend solo devuelve días con actividad; sin ceros, la línea uniría días lejanos como si fueran seguidos. */
export function fillDays(items: Row[], days: number, today = new Date()): Row[] {
  if (!items.length) return [];
  const plays = new Map(items.map((item) => [String(item.bucket).slice(0, 10), item.plays]));
  return Array.from({ length: days }, (_, index) => {
    const bucket = localDay(new Date(today.getFullYear(), today.getMonth(), today.getDate() - (days - 1 - index)));
    return { bucket, plays: plays.get(bucket.slice(0, 10)) ?? 0 };
  });
}

export function fillHours(items: Row[], hours: number, now = new Date()): Row[] {
  if (!items.length) return [];
  const plays = new Map(items.map((item) => [String(item.bucket).slice(0, 13), item.plays]));
  return Array.from({ length: hours }, (_, index) => {
    const hour = new Date(now.getFullYear(), now.getMonth(), now.getDate(), now.getHours() - (hours - 1 - index));
    const bucket = `${localDay(hour).slice(0, 10)}T${pad(hour.getHours())}:00:00`;
    return { bucket, plays: plays.get(bucket.slice(0, 13)) ?? 0 };
  });
}

export const playsRows = (body: { items: Row[] }) => fillDays(body.items, 30);

export const shortLabel = (label: string, max = 25) =>
  label.length > max ? `${label.slice(0, max).trimEnd()}…` : label;

/** El eje recorta; el tooltip y la tabla conservan el nombre completo. */
const namedAxis = (max: number) => ({
  grid: { display: false },
  ticks: {
    callback(this: Scale, value: string | number) {
      return shortLabel(this.getLabelForValue(Number(value)), max);
    },
  },
});

export const playsColumns: Column[] = [
  { key: "bucket", label: "Día", format: formatDay as never },
  { key: "plays", label: "Reproducciones" },
];

export const hourlyRows = (body: { items: Row[] }) => fillHours(body.items, 48);

export const hourlyColumns: Column[] = [
  { key: "bucket", label: "Hora", format: formatHour as never },
  { key: "plays", label: "Reproducciones" },
];

export const playsChart = (rows: Row[]) => timeLine(rows, formatDay);
export const hourlyChart = (rows: Row[]) => timeLine(rows, formatHour);

function timeLine(rows: Row[], format: (value: string) => string): ChartConfiguration {
  return {
    type: "line",
    data: {
      labels: rows.map((r) => format(r.bucket as string)),
      datasets: [{ label: "Reproducciones", data: rows.map((r) => r.plays as number), ...lineStyle(SERIES[0]), fill: { target: "origin", above: "rgba(240,66,138,.1)" } }],
    },
    options: {
      ...baseOptions(1),
      scales: {
        x: { grid: { display: false }, ticks: { maxRotation: 0, autoSkipPadding: 24 } },
        y: { beginAtZero: true, ticks: { precision: 0 } },
      },
    },
  };
}

/** Barras horizontales: nombres largos y orden por magnitud. */
export function rankChart(label: string, labelKey: string, valueKey: string) {
  return (rows: Row[]): ChartConfiguration => ({
    type: "bar",
    data: {
      labels: rows.map((r) => String(r[labelKey])),
      datasets: [{ label, data: rows.map((r) => r[valueKey] as number), ...barStyle(SERIES[0]) }],
    },
    options: {
      ...baseOptions(1),
      indexAxis: "y",
      scales: { x: { beginAtZero: true, ticks: { precision: 0 } }, y: namedAxis(18) },
    },
  });
}

export const retentionColumns: Column[] = [
  { key: "title", label: "Pista" },
  { key: "at_10s", label: "Llegan a 10 s" },
  { key: "at_50", label: "Llegan a la mitad" },
  { key: "at_100", label: "Llegan al final" },
];

export function retentionChart(rows: Row[]): ChartConfiguration {
  const series = retentionColumns.slice(1);
  return {
    type: "bar",
    data: {
      labels: rows.map((r) => String(r.title)),
      datasets: series.map((s, index) => ({
        label: s.label,
        data: rows.map((r) => r[s.key] as number),
        ...barStyle(SERIES[index]),
        categoryPercentage: 0.8,
        barPercentage: 0.9,
      })),
    },
    options: {
      ...baseOptions(3),
      indexAxis: "y",
      scales: { x: { beginAtZero: true, ticks: { precision: 0 } }, y: namedAxis(25) },
    },
  };
}

export const retentionHeight = (rows: Row[]) => Math.max(220, rows.length * 62 + 50);

export const releaseRows = (body: { scheduled: number; published: number }): Row[] =>
  body.scheduled + body.published === 0
    ? []
    : [
        { label: "Programados", count: body.scheduled },
        { label: "Publicados", count: body.published },
      ];

export const releaseColumns: Column[] = [
  { key: "label", label: "Estado" },
  { key: "count", label: "Pistas" },
];

export function countChart(label: string) {
  return (rows: Row[]): ChartConfiguration => ({
    type: "bar",
    data: {
      labels: rows.map((r) => String(r.label)),
      datasets: [{ label, data: rows.map((r) => r.count as number), ...barStyle(SERIES[0]) }],
    },
    options: { ...baseOptions(1), scales: { ...noGridX, y: { beginAtZero: true, ticks: { precision: 0 } } } },
  });
}

export const rankHeight = (rows: Row[]) => Math.max(180, rows.length * 28 + 40);

export const topColumns: Column[] = [
  { key: "label", label: "Nombre" },
  { key: "plays", label: "Reproducciones" },
];

export const genreColumns: Column[] = [
  { key: "genre", label: "Género" },
  { key: "plays", label: "Reproducciones" },
];

const DAYS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"];
const HOURS = Array.from({ length: 24 }, (_, hour) => pad(hour));

export function heatRows(body: { items: Row[] }): Row[] {
  if (!body.items.length) return [];
  const plays = new Map(body.items.map((item) => [`${item.dow}-${item.hour}`, item.plays]));
  return DAYS.flatMap((_, day) =>
    HOURS.map((__, hour) => ({ dow: day + 1, hour, plays: plays.get(`${day + 1}-${hour}`) ?? 0 })),
  );
}

export const heatColumns: Column[] = [
  { key: "dow", label: "Día", format: ((dow: number) => DAYS[dow - 1]) as never },
  { key: "hour", label: "Hora", format: ((hour: number) => `${pad(hour)}:00`) as never },
  { key: "plays", label: "Reproducciones" },
];

type Cell = { x: string; y: string; v: number };

export function heatmapChart(rows: Row[]): ChartConfiguration {
  const max = Math.max(1, ...rows.map((r) => r.plays as number));
  const cell = (context: ScriptableContext<"matrix">) => (context.raw as Cell).v;
  const config = {
    type: "matrix",
    data: {
      datasets: [
        {
          label: "Reproducciones",
          data: rows.map((r) => ({ x: pad(r.hour as number), y: DAYS[(r.dow as number) - 1], v: r.plays })),
          // Una sola tinta: más reproducciones, más intensa. Sin reproducciones, la celda queda neutra.
          backgroundColor: (context: ScriptableContext<"matrix">) =>
            cell(context) ? `rgba(240, 66, 138, ${0.2 + (0.8 * cell(context)) / max})` : GRID,
          borderWidth: 0,
          width: ({ chart }: ScriptableContext<"matrix">) => (chart.chartArea?.width ?? 0) / 24 - 2,
          height: ({ chart }: ScriptableContext<"matrix">) => (chart.chartArea?.height ?? 0) / 7 - 2,
        },
      ],
    },
    options: {
      ...baseOptions(1),
      interaction: { mode: "nearest", intersect: true },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            title: () => "",
            label: (item: TooltipItem<"matrix">) => {
              const { x, y, v } = item.raw as Cell;
              return `${y} ${x}:00 · ${v} reproducciones`;
            },
          },
        },
      },
      scales: {
        x: { type: "category", labels: HOURS, offset: true, grid: { display: false }, ticks: { maxRotation: 0, autoSkipPadding: 10 } },
        y: { type: "category", labels: DAYS, offset: true, reverse: false, grid: { display: false } },
      },
    },
  };
  return config as unknown as ChartConfiguration;
}

const SOURCES: Record<string, string> = { jamendo: "Jamendo", local: "Local" };

export const sourceColumns: Column[] = [
  { key: "source", label: "Fuente", format: ((source: string) => SOURCES[source] ?? source) as never },
  { key: "count", label: "Pistas" },
];

export function sourceChart(rows: Row[]): ChartConfiguration {
  return {
    type: "doughnut",
    data: {
      labels: rows.map((r) => SOURCES[r.source as string] ?? String(r.source)),
      datasets: [
        {
          data: rows.map((r) => r.count as number),
          backgroundColor: rows.map((_, index) => SERIES[index % SERIES.length]),
          borderColor: SURFACE,
          borderWidth: 2,
        },
      ],
    },
    options: { ...baseOptions(2), cutout: "64%", plugins: { legend: { position: "right" } } } as ChartOptions,
  };
}

const ROLES = [
  { key: "listener", label: "Oyentes" },
  { key: "composer", label: "Compositores" },
  { key: "admin", label: "Administradores" },
];

export const growthColumns: Column[] = [
  { key: "day", label: "Día", format: formatDay as never },
  ...ROLES,
];

export function growthChart(rows: Row[]): ChartConfiguration {
  return {
    type: "line",
    data: {
      labels: rows.map((r) => formatDay(r.day as string)),
      datasets: ROLES.map((role, index) => ({
        label: role.label,
        data: rows.map((r) => r[role.key] as number),
        ...lineStyle(SERIES[index]),
        fill: true,
        backgroundColor: `${SERIES[index]}33`,
      })),
    },
    options: {
      ...baseOptions(3),
      interaction: { mode: "index", intersect: false },
      scales: {
        x: { grid: { display: false }, ticks: { maxRotation: 0, autoSkipPadding: 24 } },
        y: { stacked: true, beginAtZero: true, ticks: { precision: 0 } },
      },
    },
  };
}

export const activityRows = (body: Record<string, number>): Row[] =>
  Object.values(body).every((value) => !value)
    ? []
    : [
        { label: "Casetes", count: body.tapes },
        { label: "Miembros", count: body.members },
        { label: "Pistas", count: body.tracks },
        { label: "Dedicatorias", count: body.dedications },
      ];

export const countColumns: Column[] = [
  { key: "label", label: "Dato" },
  { key: "count", label: "Cantidad" },
];

export const streamRows = (body: { items: Row[] }) => body.items.filter((item) => item.module === "streaming");

export const latencyColumns: Column[] = [
  { key: "minute", label: "Minuto", format: formatMinute as never },
  { key: "p50_ms", label: "p50 (ms)" },
  { key: "p95_ms", label: "p95 (ms)" },
];

export function latencyChart(rows: Row[]): ChartConfiguration {
  const series = latencyColumns.slice(1);
  return {
    type: "line",
    data: {
      labels: rows.map((r) => formatMinute(r.minute as string)),
      datasets: series.map((s, index) => ({
        label: s.label,
        data: rows.map((r) => r[s.key] as number),
        ...lineStyle(SERIES[index]),
        pointRadius: rows.length < 2 ? 4 : 0,
      })),
    },
    options: {
      ...baseOptions(2),
      interaction: { mode: "index", intersect: false },
      scales: {
        x: { grid: { display: false }, ticks: { maxRotation: 0, autoSkipPadding: 24 } },
        y: { beginAtZero: true, title: { display: true, text: "Milisegundos" } },
      },
    },
  };
}

export function errorRows(body: { items: Row[] }): Row[] {
  const totals = new Map<string, number>();
  for (const item of body.items) {
    const module = String(item.module);
    totals.set(module, (totals.get(module) ?? 0) + (item.errors as number));
  }
  return [...totals].map(([label, count]) => ({ label, count }));
}

export const errorColumns: Column[] = [
  { key: "label", label: "Módulo" },
  { key: "count", label: "Errores" },
];

const MINUTE_MS = 60_000;

/** Una fila por minuto de la ventana, con ceros: las métricas solo existen para los minutos con peticiones. */
export function trafficRows(body: { items: Row[] }, minutes = 60, now = new Date()): Row[] {
  if (!body.items.length) return [];
  const totals = new Map<number, { ok: number; errors: number }>();
  for (const item of body.items) {
    const minute = new Date(item.minute as string).getTime();
    const total = totals.get(minute) ?? { ok: 0, errors: 0 };
    total.ok += (item.count as number) - (item.errors as number);
    total.errors += item.errors as number;
    totals.set(minute, total);
  }
  const last = Math.floor(now.getTime() / MINUTE_MS) * MINUTE_MS;
  return Array.from({ length: minutes }, (_, index) => {
    const minute = last - (minutes - 1 - index) * MINUTE_MS;
    return { minute: new Date(minute).toISOString(), ...(totals.get(minute) ?? { ok: 0, errors: 0 }) };
  });
}

export const trafficColumns: Column[] = [
  { key: "minute", label: "Minuto", format: formatMinute as never },
  { key: "ok", label: "Correctas" },
  { key: "errors", label: "Con error" },
];

export function trafficChart(rows: Row[]): ChartConfiguration {
  const series = trafficColumns.slice(1);
  return {
    type: "bar",
    data: {
      labels: rows.map((r) => formatMinute(r.minute as string)),
      datasets: series.map((s, index) => ({
        label: s.label,
        data: rows.map((r) => r[s.key] as number),
        ...barStyle(SERIES[index]),
      })),
    },
    options: {
      ...baseOptions(2),
      interaction: { mode: "index", intersect: false },
      scales: {
        x: { stacked: true, grid: { display: false }, ticks: { maxRotation: 0, autoSkipPadding: 24 } },
        y: { stacked: true, beginAtZero: true, title: { display: true, text: "Peticiones por minuto" } },
      },
    },
  };
}

/** El p95 de una hora no se puede sacar de los p95 por minuto, así que se muestra el peor minuto. */
export function moduleRows(body: { items: Row[] }): { module: string; count: number; p95: number; errors: number }[] {
  const totals = new Map<string, { module: string; count: number; p95: number; errors: number }>();
  for (const item of body.items) {
    const module = String(item.module);
    const total = totals.get(module) ?? { module, count: 0, p95: 0, errors: 0 };
    total.count += item.count as number;
    total.errors += item.errors as number;
    total.p95 = Math.max(total.p95, item.p95_ms as number);
    totals.set(module, total);
  }
  return [...totals.values()].sort((a, b) => b.count - a.count);
}
