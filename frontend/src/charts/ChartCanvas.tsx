import { Chart, type ChartConfiguration } from "chart.js";
import { useEffect, useRef } from "react";
import { useTheme } from "../theme";
import { applyChartTheme } from "./index";

type Props = { config: ChartConfiguration; label: string; onChart?: (chart: Chart | null) => void };

export function ChartCanvas({ config, label, onChart }: Props) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const { resolved } = useTheme();

  useEffect(() => {
    if (!canvas.current) return;
    applyChartTheme();
    const chart = new Chart(canvas.current, config);
    onChart?.(chart);
    return () => {
      onChart?.(null);
      chart.destroy();
    };
  }, [config, onChart, resolved]);

  return <canvas ref={canvas} role="img" aria-label={label} />;
}
