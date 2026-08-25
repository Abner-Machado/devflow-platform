/** Application chrome: sidebar, topbar and the routed content area. */

import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";

import { useTheme } from "../../hooks/useTheme";
import { useAuth } from "../../auth/useAuth";
import {
  IconActivity,
  IconApi,
  IconDashboard,
  IconDocs,
  IconLogout,
  IconMenu,
  IconMetrics,
  IconMoon,
  IconProjects,
  IconSettings,
  IconSun,
  IconTasks,
} from "../Icons";
import { Avatar, Button } from "../ui/Primitives";

const NAV = [
  { to: "/", label: "Dashboard", icon: IconDashboard, end: true },
  { to: "/projects", label: "Projects", icon: IconProjects },
  { to: "/tasks", label: "Tasks", icon: IconTasks },
  { to: "/documentation", label: "Documentation", icon: IconDocs },
  { to: "/activity", label: "Activity", icon: IconActivity },
  { to: "/metrics", label: "Metrics", icon: IconMetrics },
];

const PAGE_TITLES: Record<string, string> = {
  "/": "Dashboard",
  "/projects": "Projects",
  "/tasks": "Tasks",
  "/documentation": "Documentation",
  "/activity": "Activity",
  "/metrics": "Metrics",
  "/settings": "Settings",
};

export function AppLayout() {
  const { user, logout } = useAuth();
  const { theme, toggle } = useTheme();
  const location = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);

  // A route change closes the mobile drawer; otherwise it hides the page.
  useEffect(() => {
    setMenuOpen(false);
  }, [location.pathname]);

  const title =
    PAGE_TITLES[location.pathname] ??
    (location.pathname.startsWith("/projects/") ? "Project" : "DevFlow");

  return (
    <div className="app-shell">
      {menuOpen && (
        <div className="sidebar-scrim" onClick={() => setMenuOpen(false)} aria-hidden="true" />
      )}

      <aside className={menuOpen ? "sidebar is-open" : "sidebar"}>
        <NavLink to="/" className="sidebar-brand">
          <span className="sidebar-mark" aria-hidden="true">
            D
          </span>
          DevFlow
        </NavLink>

        <nav aria-label="Main">
          {NAV.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) => (isActive ? "nav-link is-active" : "nav-link")}
            >
              <Icon />
              {label}
            </NavLink>
          ))}
        </nav>

        <p className="sidebar-section">Developer</p>
        <a className="nav-link" href="/docs" target="_blank" rel="noreferrer">
          <IconApi />
          API reference
        </a>
        <NavLink
          to="/settings"
          className={({ isActive }) => (isActive ? "nav-link is-active" : "nav-link")}
        >
          <IconSettings />
          Settings
        </NavLink>

        <div className="sidebar-footer">
          <div className="row">
            <Avatar name={user?.full_name ?? "?"} />
            <div style={{ minWidth: 0 }}>
              <p className="truncate" style={{ fontSize: "var(--text-sm)", fontWeight: 600 }}>
                {user?.full_name}
              </p>
              <p className="truncate subtle">{user?.email}</p>
            </div>
          </div>
          <Button variant="ghost" size="sm" onClick={() => void logout()}>
            <IconLogout />
            Sign out
          </Button>
        </div>
      </aside>

      <div className="app-main">
        <header className="topbar">
          <Button
            variant="ghost"
            className="button-icon menu-button"
            onClick={() => setMenuOpen((open) => !open)}
            aria-label="Toggle navigation"
            aria-expanded={menuOpen}
          >
            <IconMenu />
          </Button>
          <span className="topbar-title">{title}</span>
          <span className="spacer" />
          <Button
            variant="ghost"
            className="button-icon"
            onClick={toggle}
            aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}
          >
            {theme === "dark" ? <IconSun /> : <IconMoon />}
          </Button>
        </header>

        <main className="app-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
