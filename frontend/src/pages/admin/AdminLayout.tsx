import { NavLink, Outlet } from "react-router-dom";

const sections = [
  { to: "/admin", label: "Panel" },
  { to: "/admin/users", label: "Usuarios" },
  { to: "/admin/requests", label: "Solicitudes" },
  { to: "/admin/catalog", label: "Catálogo" },
  { to: "/admin/audit", label: "Auditoría" },
  { to: "/admin/health", label: "Salud" },
];

export function AdminLayout() {
  return (
    <>
      <h1 className="page-title">Administración</h1>
      <nav className="subnav" aria-label="Secciones de administración">
        {sections.map((section) => (
          <NavLink key={section.to} to={section.to} end={section.to === "/admin"}>{section.label}</NavLink>
        ))}
      </nav>
      <Outlet />
    </>
  );
}
