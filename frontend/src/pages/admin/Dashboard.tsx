import { useMemo } from "react";
import { ChartCard, type Row } from "../../charts/ChartCard";
import {
  activityRows,
  browserZone,
  countChart,
  countColumns,
  errorColumns,
  errorRows,
  genreColumns,
  growthChart,
  growthColumns,
  heatColumns,
  heatmapChart,
  heatRows,
  hourlyChart,
  hourlyColumns,
  hourlyRows,
  latencyChart,
  latencyColumns,
  playsChart,
  playsColumns,
  playsRows,
  rankChart,
  rankHeight,
  releaseColumns,
  releaseRows,
  sourceChart,
  sourceColumns,
  streamRows,
  topColumns,
} from "../../charts/definitions";
import { HealthCards } from "./Health";

const topChart = rankChart("Reproducciones", "label", "plays");
const genreChart = rankChart("Reproducciones", "genre", "plays");
const errorChart = rankChart("Errores", "label", "count");
const releaseChart = countChart("Pistas");
const activityChart = countChart("Cantidad");
const duplicateRows = (body: { duplicates_discarded: number }): Row[] => [
  { label: "Eventos descartados", count: body.duplicates_discarded },
];
const duplicateStat = (rows: Row[]) => <p className="stat">{String(rows[0].count)}</p>;

const heatScale = (
  <div className="heat-scale" aria-hidden="true">
    <span>Menos</span>
    <i />
    <span>Más</span>
  </div>
);

export function Dashboard() {
  const zone = useMemo(() => encodeURIComponent(browserZone()), []);
  return (
    <>
      <HealthCards />
      <div className="charts">
        <ChartCard title="Reproducciones por día" subtitle="Últimos 30 días" url={`/api/metrics/plays?scope=global&group=day&days=30&tz=${zone}`} rows={playsRows as never} columns={playsColumns} chart={playsChart} report="plays" tall />
        <ChartCard title="Reproducciones por hora" subtitle="Últimas 48 horas" url={`/api/metrics/plays?scope=global&group=hour&days=3&tz=${zone}`} rows={hourlyRows as never} columns={hourlyColumns} chart={hourlyChart} report="plays-hourly" tall />
        <ChartCard title="Top canciones" url="/api/metrics/top?scope=global&kind=songs&limit=10" columns={topColumns} chart={topChart} height={rankHeight} report="top" />
        <ChartCard title="Top artistas" url="/api/metrics/top?scope=global&kind=artists&limit=10" columns={topColumns} chart={topChart} height={rankHeight} report="top-artists" />
        <ChartCard title="Distribución por género" url="/api/metrics/genres?scope=global" columns={genreColumns} chart={genreChart} height={rankHeight} report="genres" />
        <ChartCard title="Catálogo por fuente" url="/api/metrics/catalog-sources" columns={sourceColumns} chart={sourceChart} report="catalog-sources" />
        <ChartCard title="Día de la semana y hora" subtitle="Últimos 30 días" url={`/api/metrics/heatmap?days=30&tz=${zone}`} rows={heatRows as never} columns={heatColumns} chart={heatmapChart} note={heatScale} report="heatmap" tall />
        <ChartCard title="Crecimiento de usuarios por rol" subtitle="Acumulado, según el rol actual" url="/api/metrics/user-growth?days=30" columns={growthColumns} chart={growthChart} report="user-growth" tall />
        <ChartCard title="Actividad en casetes" url="/api/metrics/tape-activity" rows={activityRows as never} columns={countColumns} chart={activityChart} report="tape-activity" />
        <ChartCard title="Programados y publicados" url="/api/metrics/releases?scope=global" rows={releaseRows as never} columns={releaseColumns} chart={releaseChart} report="releases" />
        <ChartCard title="Latencia del streaming" subtitle="Última hora, p50 y p95" url="/api/metrics/latency?minutes=60" rows={streamRows as never} columns={latencyColumns} chart={latencyChart} report="latency" tall />
        <ChartCard title="Errores por módulo" subtitle="Última hora" url="/api/metrics/latency?minutes=60" rows={errorRows as never} columns={errorColumns} chart={errorChart} height={rankHeight} report="latency" />
        <ChartCard title="Duplicados descartados" subtitle="Eventos repetidos que no contaron" url="/api/metrics/duplicates" rows={duplicateRows as never} columns={countColumns} stat={duplicateStat} report="duplicates" />
      </div>
    </>
  );
}
