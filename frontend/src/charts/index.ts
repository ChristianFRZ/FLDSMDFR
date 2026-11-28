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
 * Orden fijo, validado con el script de la skill dataviz sobre las dos superficies de las tarjetas (oscura #2E2C35 y
 * clara #FBF9F4): pasa banda de luminosidad, croma, daltonismo y contraste. Son tonos derivados de la marca.
 */
export const SERIES = ["#F0428A", "#B08600", "#009E8F", "#6172FF"] as const;

const SURFACES = {
  dark: { ink: "#F4F1EA", mute: "#BDB9AF", grid: "#3D3B45", surface: "#2E2C35", tip: "#141317" },
  light: { ink: "#141317", mute: "#5C5A63", grid: "#DDD6C6", surface: "#FBF9F4", tip: "#FBF9F4" },
} as const;

const currentTheme = () => (document.documentElement.dataset.theme === "light" ? "light" : "dark");
export const GRID_COLOR = () => SURFACES[currentTheme()].grid;
export const SURFACE_COLOR = () => SURFACES[currentTheme()].surface;

/** Chart.js lee sus valores al crear la gráfica: se vuelven a fijar con el tema vigente antes de cada una. */
export function applyChartTheme() {
  const c = SURFACES[currentTheme()];
  Chart.defaults.color = c.mute;
  Chart.defaults.borderColor = c.grid;
  Chart.defaults.plugins.tooltip.backgroundColor = c.tip;
  Chart.defaults.plugins.tooltip.titleColor = c.ink;
  Chart.defaults.plugins.tooltip.bodyColor = c.ink;
  Chart.defaults.plugins.tooltip.borderColor = c.ink;
}
applyChartTheme();

Chart.defaults.font.family = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
Chart.defaults.font.size = 12;
Chart.defaults.plugins.legend.labels.boxWidth = 10;
Chart.defaults.plugins.legend.labels.boxHeight = 10;
Chart.defaults.plugins.tooltip.borderWidth = 1;

/** Sin este fondo, el PNG exportado sale transparente y el texto no se lee. */
Chart.register({
  id: "surface",
  beforeDraw({ ctx, width, height }) {
    ctx.save();
    ctx.fillStyle = SURFACE_COLOR();
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
  pointHoverBorderColor: SURFACE_COLOR(),
  pointHoverBorderWidth: 2,
  // Monótona: una curva libre sube más allá del dato real y baja de cero entre días sin actividad.
  cubicInterpolationMode: "monotone" as const,
});

export const noGridX = { x: { grid: { display: false } } };
