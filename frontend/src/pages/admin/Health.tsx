import { useQuery } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { api } from "../../api/client";
import { ChartCard } from "../../charts/ChartCard";
import { moduleRows, trafficChart, trafficColumns, trafficRows } from "../../charts/definitions";
import { Icon, type IconName } from "../../components/Icon";

type Service = { name: string; status: string; uptime_seconds?: number; ms?: number; lag_seconds?: number | null };
type Latency = { items: Record<string, unknown>[] };
type System = {
  disk: { used_bytes: number; total_bytes: number } | null;
  database: { size_bytes: number; connections: number; max_connections: number };
  system: { version: string; started_at: string; python: string; postgres: string };
};
type Activity = { minutes: number; listeners: number; plays: number };

const REFRESH_MS = 15_000;
const ACTIVITY_REFRESH_MS = 30 * 60_000;
const LATENCY_URL = "/api/metrics/latency?minutes=60";

const names: Record<string, string> = {
  app: "Aplicación",
  database: "Base de datos",
  jamendo: "Jamendo",
  aggregates: "Agregados",
};

const modules: Record<string, string> = {
  analytics: "Analítica",
  catalog: "Catálogo",
  playback: "Reproducción",
  playlists: "Playlists",
  social: "Casetes y social",
  streaming: "Streaming",
  users: "Usuarios",
};

const states: Record<string, { label: string; icon: IconName }> = {
  up: { label: "En línea", icon: "check" },
  down: { label: "Caído", icon: "close" },
  delayed: { label: "Con retraso", icon: "bell" },
  not_configured: { label: "Sin configurar", icon: "link" },
};

const number = new Intl.NumberFormat("es-MX", { maximumFractionDigits: 1 });
const time = new Intl.DateTimeFormat("es-MX", { hour: "2-digit", minute: "2-digit" });
const fullTime = new Intl.DateTimeFormat("es-MX", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
const date = new Intl.DateTimeFormat("es-MX", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });

function span(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)} s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)} min`;
  if (seconds < 86_400) return `${Math.floor(seconds / 3600)} h`;
  return `${Math.floor(seconds / 86_400)} d`;
}

function bytes(value: number): string {
  const gb = value / 1024 ** 3;
  return gb >= 1 ? `${number.format(gb)} GB` : `${number.format(value / 1024 ** 2)} MB`;
}

function detail(service: Service): string | null {
  if (service.uptime_seconds !== undefined) return `activa hace ${span(service.uptime_seconds)}`;
  if (service.ms !== undefined) return `responde en ${number.format(service.ms)} ms`;
  if (service.lag_seconds != null) return `${span(service.lag_seconds)} sin actualizar`;
  return null;
}

function useHealth() {
  return useQuery({
    queryKey: ["admin-health"],
    queryFn: () => api<{ services: Service[] }>("/api/admin/health"),
    refetchInterval: REFRESH_MS,
  });
}

export function HealthCards() {
  const health = useHealth();
  if (health.isError) return <p className="muted">Datos no disponibles por ahora</p>;
  if (health.isPending) return <p className="muted" role="status">Consultando servicios…</p>;
  return (
    <ul className="health" aria-label="Salud del sistema">
      {health.data.services.map((service) => {
        const state = states[service.status] ?? { label: service.status, icon: "bell" as const };
        const extra = detail(service);
        return (
          <li key={service.name} data-status={service.status}>
            <Icon name={state.icon} />
            <div>
              <b>{names[service.name] ?? service.name}</b>
              <small>{extra ? `${state.label} · ${extra}` : state.label}</small>
            </div>
          </li>
        );
      })}
    </ul>
  );
}

function summary(services: Service[]): { level: string; text: string } {
  const down = services.filter((service) => service.status === "down").length;
  const delayed = services.filter((service) => service.status === "delayed").length;
  if (down) return { level: "down", text: down === 1 ? "1 servicio caído" : `${down} servicios caídos` };
  if (delayed) return { level: "delayed", text: delayed === 1 ? "1 servicio con retraso" : `${delayed} servicios con retraso` };
  return { level: "up", text: "Todo en orden" };
}

function HealthSummary() {
  const health = useHealth();
  if (!health.data) return null;
  const { level, text } = summary(health.data.services);
  return (
    <div className="health-summary" data-level={level} role="status">
      <b>{text}</b>
      <small>Revisado a las {fullTime.format(health.dataUpdatedAt)}</small>
    </div>
  );
}

function Modules() {
  const query = useQuery({
    queryKey: ["metric", LATENCY_URL],
    queryFn: () => api<Latency>(LATENCY_URL),
    refetchInterval: REFRESH_MS,
  });
  const rows = query.data ? moduleRows(query.data) : [];
  return (
    <figure className="chart chart-tall">
      <figcaption><div><h3>Módulos</h3><small>Última hora</small></div></figcaption>
      {query.isPending && <div className="chart-state" role="status">Cargando…</div>}
      {query.isError && <div className="chart-state">Datos no disponibles por ahora</div>}
      {query.isSuccess && !rows.length && <div className="chart-state">Aún no hay datos</div>}
      {rows.length > 0 && (
        <div className="chart-table">
          <table aria-label="Módulos">
            <thead>
              <tr>
                <th scope="col">Módulo</th>
                <th className="num" scope="col">Peticiones</th>
                <th className="num" scope="col">p95 más alto</th>
                <th className="num" scope="col">Errores</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.module}>
                  <td>{modules[row.module] ?? row.module}</td>
                  <td className="num">{number.format(row.count)}</td>
                  <td className="num">{number.format(row.p95)} ms</td>
                  <td className="num">{number.format(row.errors)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </figure>
  );
}

function Fact({ label, value, children }: { label: string; value: string; children?: ReactNode }) {
  return <div><dt>{label}</dt><dd>{value}{children}</dd></div>;
}

function SystemCards() {
  const query = useQuery({
    queryKey: ["admin-health-system"],
    queryFn: () => api<System>("/api/admin/health/system"),
    refetchInterval: REFRESH_MS,
  });
  if (query.isPending) return <figure className="chart"><div className="chart-state" role="status">Cargando…</div></figure>;
  if (query.isError) return <figure className="chart"><div className="chart-state">Datos no disponibles por ahora</div></figure>;
  const { disk, database, system } = query.data;
  return (
    <>
      <figure className="chart">
        <figcaption><div><h3>Recursos</h3></div></figcaption>
        <dl className="health-facts">
          {disk && (
            <Fact label="Disco de audios" value={`${bytes(disk.used_bytes)} de ${bytes(disk.total_bytes)}`}>
              <progress className="health-meter" aria-label="Disco de audios usado" value={disk.used_bytes} max={disk.total_bytes} />
            </Fact>
          )}
          <Fact label="Base de datos" value={bytes(database.size_bytes)} />
          <Fact label="Conexiones abiertas" value={`${database.connections} de ${database.max_connections}`} />
        </dl>
      </figure>
      <figure className="chart">
        <figcaption><div><h3>Datos del sistema</h3></div></figcaption>
        <dl className="health-facts">
          <Fact label="Versión" value={system.version} />
          <Fact label="Encendida desde" value={date.format(new Date(system.started_at))} />
          <Fact label="Python" value={system.python} />
          <Fact label="PostgreSQL" value={system.postgres} />
        </dl>
      </figure>
    </>
  );
}

function ActivityCard() {
  const query = useQuery({
    queryKey: ["admin-health-activity"],
    queryFn: () => api<Activity>("/api/admin/health/activity"),
    refetchInterval: ACTIVITY_REFRESH_MS,
    staleTime: ACTIVITY_REFRESH_MS,
  });
  return (
    <figure className="chart">
      <figcaption>
        <div>
          <h3>Actividad</h3>
          {query.data && <small>Últimos {query.data.minutes} minutos · actualizado a las {time.format(query.dataUpdatedAt)}</small>}
        </div>
      </figcaption>
      {query.isPending && <div className="chart-state" role="status">Cargando…</div>}
      {query.isError && <div className="chart-state">Datos no disponibles por ahora</div>}
      {query.data && (
        <div className="health-numbers">
          <div><b>{number.format(query.data.listeners)}</b><small>Oyentes</small></div>
          <div><b>{number.format(query.data.plays)}</b><small>Reproducciones</small></div>
        </div>
      )}
    </figure>
  );
}

const rowsForTraffic = (body: Latency) => trafficRows(body);

export function Health() {
  return (
    <div className="health-page">
      <HealthSummary />
      <HealthCards />
      <div className="charts">
        <ChartCard
          title="Tendencia de tráfico"
          subtitle="Última hora, por minuto"
          url={LATENCY_URL}
          rows={rowsForTraffic as never}
          columns={trafficColumns}
          chart={trafficChart}
          refresh={REFRESH_MS}
          tall
        />
        <Modules />
        <SystemCards />
        <ActivityCard />
      </div>
    </div>
  );
}
