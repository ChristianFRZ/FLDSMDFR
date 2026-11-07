import { Chart, type ChartConfiguration } from "chart.js";
import { useEffect, useRef } from "react";
import "./index";

type Props = { config: ChartConfiguration; label: string; onChart?: (chart: Chart | null) => void };

export function ChartCanvas({ config, label, onChart }: Props) {
  const canvas = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    if (!canvas.current) return;
    const chart = new Chart(canvas.current, config);
    onChart?.(chart);
    return () => {
      onChart?.(null);
      chart.destroy();
    };
  }, [config, onChart]);

  return <canvas ref={canvas} role="img" aria-label={label} />;
}
