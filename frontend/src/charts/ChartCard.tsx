import { useQuery } from "@tanstack/react-query";
import type { Chart, ChartConfiguration } from "chart.js";
import { type ReactNode, useCallback, useMemo, useRef, useState } from "react";
import { api } from "../api/client";
import { ChartCanvas } from "./ChartCanvas";
import { exportCsv, exportPng } from "./export";

export type Column = { key: string; label: string; format?: (value: never) => string };
export type Row = Record<string, unknown>;

type Props = {
  title: string;
  subtitle?: string;
  url: string;
  columns: Column[];
  /** De la respuesta a filas. Por defecto toma `items`. */
  rows?: (body: never) => Row[];
  chart?: (rows: Row[]) => ChartConfiguration;
  /** Para cifras que se leen mejor sin gráfica. */
  stat?: (rows: Row[]) => ReactNode;
  /** Nombre del reporte en el backend. Con él, la tarjeta ofrece CSV y PNG. */
  report?: string;
  /** Va bajo la gráfica, por ejemplo la escala de un mapa de calor. */
  note?: ReactNode;
  tall?: boolean;
  /** Alto según los datos, para que las barras no se aplasten con muchas filas. */
  height?: (rows: Row[]) => number;
  /** Cada cuántos milisegundos vuelve a pedir los datos. Sin él, se piden una vez. */
  refresh?: number;
};

const defaultRows = (body: { items?: Row[] }) => body.items ?? [];

function cell(column: Column, row: Row): string {
  const value = row[column.key];
  return column.format ? column.format(value as never) : String(value ?? "");
}

/** Una gráfica que falla no tumba la página (F7.3), y siempre hay tabla como alternativa. */
export function ChartCard({ title, subtitle, url, columns, rows = defaultRows as never, chart, stat, report, note, tall, height, refresh }: Props) {
  const [showTable, setShowTable] = useState(false);
  const instance = useRef<Chart | null>(null);
  const [, redraw] = useState(0);
  const [exportFailed, setExportFailed] = useState(false);
  const query = useQuery({ queryKey: ["metric", url], queryFn: () => api<unknown>(url), refetchInterval: refresh });
  const data = useMemo(() => (query.data ? rows(query.data as never) : []), [query.data, rows]);
  const config = useMemo(() => (chart && data.length ? chart(data) : null), [chart, data]);
  const keep = useCallback((created: Chart | null) => {
    instance.current = created;
    redraw((n) => n + 1);
  }, []);

  return (
    <figure className={tall ? "chart chart-tall" : "chart"}>
      <figcaption>
        <div>
          <h3>{title}</h3>
          {subtitle && <small>{subtitle}</small>}
        </div>
        <div className="chart-actions">
          {data.length > 0 && (
            <button
              className="link"
              type="button"
              aria-label={`${showTable ? "Ver gráfica" : "Ver tabla"} de ${title}`}
              aria-expanded={showTable}
              onClick={() => setShowTable(!showTable)}
            >
              {showTable ? "Gráfica" : "Tabla"}
            </button>
          )}
          {data.length > 0 && report && (
            <button
              className="link"
              type="button"
              aria-label={`Exportar ${title} a CSV`}
              onClick={() => {
                setExportFailed(false);
                exportCsv(report).catch(() => setExportFailed(true));
              }}
            >
              CSV
            </button>
          )}
          {data.length > 0 && report && instance.current && (
            <button
              className="link"
              type="button"
              aria-label={`Exportar ${title} a PNG`}
              onClick={() => instance.current && exportPng(instance.current, report)}
            >
              PNG
            </button>
          )}
        </div>
      </figcaption>
      {exportFailed && <p className="form-error" role="alert">No se pudo exportar. Intenta de nuevo.</p>}
      {query.isPending && <div className="chart-state" role="status">Cargando…</div>}
      {query.isError && <div className="chart-state">Datos no disponibles por ahora</div>}
      {query.isSuccess && !data.length && <div className="chart-state">Aún no hay datos</div>}
      {data.length > 0 && !showTable && stat?.(data)}
      {data.length > 0 && !showTable && config && (
        <div className="chart-canvas" style={height ? { height: height(data) } : undefined}><ChartCanvas config={config} label={title} onChart={keep} /></div>
      )}
      {data.length > 0 && !showTable && note}
      {data.length > 0 && showTable && (
        <div className="chart-table">
          <table aria-label={title}>
            <thead><tr>{columns.map((c) => <th key={c.key} scope="col">{c.label}</th>)}</tr></thead>
            <tbody>
              {data.map((row, index) => (
                <tr key={index}>{columns.map((c) => <td key={c.key}>{cell(c, row)}</td>)}</tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </figure>
  );
}
