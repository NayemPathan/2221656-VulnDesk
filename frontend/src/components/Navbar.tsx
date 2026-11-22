import React from "react";
import { Link, NavLink, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { RoleBadge } from "./Badges";
import { useTheme } from "../context/ThemeContext";

function NavIcon({ name }: { name: string }) {
  const props = {
    className: "nav-icon",
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 2,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    "aria-hidden": true,
  };

  switch (name) {
    case "dashboard":
      return (
        <svg {...props}>
          <rect x="3" y="3" width="7" height="9" rx="1" />
          <rect x="14" y="3" width="7" height="5" rx="1" />
          <rect x="14" y="12" width="7" height="9" rx="1" />
          <rect x="3" y="16" width="7" height="5" rx="1" />
        </svg>
      );
    case "reports":
      return (
        <svg {...props}>
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
          <line x1="8" y1="13" x2="16" y2="13" />
          <line x1="8" y1="17" x2="13" y2="17" />
        </svg>
      );
    case "new":
      return (
        <svg {...props}>
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="8" x2="12" y2="16" />
          <line x1="8" y1="12" x2="16" y2="12" />
        </svg>
      );
    case "groups":
      return (
        <svg {...props}>
          <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
          <circle cx="9" cy="7" r="4" />
          <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
          <path d="M16 3.13a4 4 0 0 1 0 7.75" />
        </svg>
      );
    case "admin":
      return (
        <svg {...props}>
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
        </svg>
      );
    case "profile":
      return (
        <svg {...props}>
          <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
          <circle cx="12" cy="7" r="4" />
        </svg>
      );
    case "logout":
      return (
        <svg {...props}>
          <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
          <polyline points="16 17 21 12 16 7" />
          <line x1="21" y1="12" x2="9" y2="12" />
        </svg>
      );
    case "login":
      return (
        <svg {...props}>
          <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4" />
          <polyline points="10 17 15 12 10 7" />
          <line x1="15" y1="12" x2="3" y2="12" />
        </svg>
      );
    default:
      return null;
  }
}

export const Navbar: React.FC = () => {
  const { currentUser, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const location = useLocation();
  const navigate = useNavigate();


  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };


  return (
    <header className="navbar">
      <div className="navbar-container">
        <div className="navbar-left">
          <Link to="/" className="navbar-brand">
            <span className="brand-shield">🛡️</span>
            <div>
              <span className="brand-title">VulnDesk</span>
              <span className="brand-subtitle">Vulnerability Triage &amp; RBAC</span>
            </div>
          </Link>


          {currentUser && (
            <nav className="navbar-links">
              <Link
                to="/"
                className={
                  location.pathname === "/"
                    ? "nav-btn nav-link active"
                    : "nav-btn nav-link"
                }
              >
                <NavIcon name="reports" /> Reports
              </Link>
              <Link
                to="/dashboard"
                className={
                  location.pathname === "/dashboard"
                    ? "nav-btn nav-link active"
                    : "nav-btn nav-link"
                }
              >
                <NavIcon name="dashboard" /> Dashboard
              </Link>
              <NavLink
                to="/groups"
                className={({ isActive }) =>
                  isActive
                    ? "nav-btn nav-link active"
                    : "nav-btn nav-link"
                }
              >
                <NavIcon name="groups" /> Groups
              </NavLink>
              {currentUser.role === "researcher" && (
                <Link
                  to="/reports/new"
                  className={
                    location.pathname === "/reports/new"
                      ? "nav-btn nav-link nav-cta active"
                      : "nav-btn nav-link nav-cta"
                  }
                >
                  <NavIcon name="new" /> Submit
                </Link>
              )}
              {currentUser.role === "admin" && (
                <Link
                  to="/admin/users"
                  className={
                    location.pathname === "/admin/users"
                      ? "nav-btn nav-link active"
                      : "nav-btn nav-link"
                  }
                >
                  <NavIcon name="admin" /> Administration
                </Link>
              )}
            </nav>
          )}
        </div>


        <div className="navbar-right navbar-user">
          <button
            type="button"
            className="btn btn-secondary btn-sm theme-toggle-btn"
            onClick={toggleTheme}
            title="Toggle Light / Dark Theme"
          >
            {theme === "dark" ? "☀️ Light" : "🌙 Dark"}
          </button>
          {currentUser ? (
            <>
              <Link to="/profile" className="nav-btn nav-link">
                <NavIcon name="profile" /> Profile
              </Link>
              <RoleBadge
                role={currentUser.role}
                isBanned={currentUser.is_banned}
              />
              <button
                type="button"
                className="btn btn-secondary btn-sm nav-btn"
                onClick={handleLogout}
              >
                <NavIcon name="logout" /> Sign Out
              </button>
            </>
          ) : (
            <div className="navbar-links">
              <Link to="/login" className="nav-btn nav-link">
                <NavIcon name="login" /> Sign In
              </Link>
              <Link to="/register" className="nav-btn nav-link nav-cta">
                <NavIcon name="login" /> Register
              </Link>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
