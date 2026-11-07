import { useMemo } from "react";
import { ChartCard, type Row } from "../../charts/ChartCard";
import {
  browserZone,
  countChart,
  playsChart,
  playsColumns,
  playsRows,
  releaseColumns,
  releaseRows,
  retentionChart,
  retentionColumns,
  retentionHeight,
} from "../../charts/definitions";

const inclusionRows = (body: { playlists: number; tapes: number }): Row[] =>
  body.playlists + body.tapes === 0
    ? []
    : [
        { label: "Casetes", count: body.tapes },
        { label: "Playlists", count: body.playlists },
      ];

export function ComposerStats() {
  const plays = useMemo(() => `/api/metrics/plays?scope=composer&tz=${encodeURIComponent(browserZone())}`, []);
  return (
    <>
    <h1 className="page-title">Estadísticas de tu música</h1>
    <div className="charts">
      <ChartCard title="Reproducciones por día" subtitle="Últimos 30 días, solo tus pistas" url={plays} rows={playsRows as never} columns={playsColumns} chart={playsChart} tall />
      <ChartCard title="Retención por pista" subtitle="Cuántas reproducciones llegan a cada punto" url="/api/metrics/retention" columns={retentionColumns} chart={retentionChart} height={retentionHeight} tall />
      <ChartCard
        title="Programados y publicados"
        url="/api/metrics/releases?scope=composer"
        rows={releaseRows as never}
        columns={releaseColumns}
        chart={countChart("Pistas")}
      />
      <ChartCard
        title="Dónde están tus pistas"
        subtitle="Solo un conteo, sin identidades"
        url="/api/metrics/inclusions"
        rows={inclusionRows as never}
        columns={[{ key: "label", label: "Lugar" }, { key: "count", label: "Cantidad" }]}
        chart={countChart("Cantidad")}
      />
    </div>
    </>
  );
}
