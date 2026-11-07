import { Link } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { ChartCard } from "../charts/ChartCard";
import { genreColumns, rankChart, rankHeight, topColumns } from "../charts/definitions";

const topChart = rankChart("Reproducciones", "label", "plays");
const genreChart = rankChart("Reproducciones", "genre", "plays");

export function Stats() {
  const { user } = useAuth();
  return (
    <>
      <h1 className="page-title">Lo que escuchas</h1>
      {user?.role === "composer" && <p><Link to="/composer/stats">Ver las estadísticas de tu música</Link></p>}
      {user?.role === "admin" && <p><Link to="/admin">Ver el panel de administración</Link></p>}
      <div className="charts">
        <ChartCard title="Tus canciones más escuchadas" url="/api/metrics/top?scope=me&kind=songs&limit=10" columns={topColumns} chart={topChart} height={rankHeight} tall />
        <ChartCard title="Tus artistas" url="/api/metrics/top?scope=me&kind=artists&limit=10" columns={topColumns} chart={topChart} height={rankHeight} />
        <ChartCard title="Tus géneros" url="/api/metrics/genres?scope=me" columns={genreColumns} chart={genreChart} height={rankHeight} />
      </div>
    </>
  );
}
