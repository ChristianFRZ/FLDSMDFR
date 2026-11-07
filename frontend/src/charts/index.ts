import {
  ArcElement,
  BarController,
  BarElement,
  CategoryScale,
  Chart,
  DoughnutController,
  Filler,
  Legend,
  LinearScale,
  LineController,
  LineElement,
  PointElement,
  Tooltip,
  type ChartOptions,
} from "chart.js";
import { MatrixController, MatrixElement } from "chartjs-chart-matrix";

Chart.register(
  ArcElement,
  BarController,
  BarElement,
  CategoryScale,
  DoughnutController,
  Filler,
  Legend,
  LinearScale,
  LineController,
  LineElement,
  MatrixController,
  MatrixElement,
  PointElement,
  Tooltip,
);

/**
 * Orden fijo, validado sobre el fondo de las tarjetas (#2E2C35) con el script de la skill dataviz: pasa banda de luminosidad,
 * croma, daltonismo y contraste. Son tonos derivados de la marca; los de marca puros quedan fuera de la banda.
 */
export const SERIES = ["#F0428A", "#B08600", "#009E8F", "#6172FF"] as const;

const INK = "#F4F1EA";
const MUTE = "#BDB9AF";
export const GRID = "#3D3B45";
export const SURFACE = "#2E2C35";

Chart.defaults.color = MUTE;
Chart.defaults.font.family = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
Chart.defaults.font.size = 12;
Chart.defaults.borderColor = GRID;
Chart.defaults.plugins.legend.labels.boxWidth = 10;
Chart.defaults.plugins.legend.labels.boxHeight = 10;
Chart.defaults.plugins.tooltip.backgroundColor = "#141317";
Chart.defaults.plugins.tooltip.titleColor = INK;
Chart.defaults.plugins.tooltip.bodyColor = INK;
Chart.defaults.plugins.tooltip.borderColor = INK;
Chart.defaults.plugins.tooltip.borderWidth = 1;

/** Sin este fondo, el PNG exportado sale transparente y el texto claro no se lee. */
Chart.register({
  id: "surface",
  beforeDraw({ ctx, width, height }) {
    ctx.save();
    ctx.fillStyle = SURFACE;
    ctx.fillRect(0, 0, width, height);
    ctx.restore();
  },
});

export const reducedMotion = () => window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;

/** Una sola serie no lleva leyenda: el título ya dice qué se grafica. */
export function baseOptions(series: number): ChartOptions {
  return {
    responsive: true,
    maintainAspectRatio: false,
    animation: reducedMotion() ? false : { duration: 300 },
    interaction: { mode: "nearest", intersect: false },
    plugins: { legend: { display: series >= 2, position: "top", align: "start" } },
  };
}

export const barStyle = (color: string) => ({
  backgroundColor: color,
  borderRadius: 4,
  borderSkipped: "start" as const,
  maxBarThickness: 24,
});

export const lineStyle = (color: string) => ({
  borderColor: color,
  backgroundColor: color,
  borderWidth: 2,
  pointRadius: 0,
  pointHoverRadius: 5,
  pointHoverBorderColor: SURFACE,
  pointHoverBorderWidth: 2,
  // Monótona: una curva libre sube más allá del dato real y baja de cero entre días sin actividad.
  cubicInterpolationMode: "monotone" as const,
});

export const noGridX = { x: { grid: { display: false } } };
