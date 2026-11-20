import React from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { RoleBadge } from "./Badges";
import { useTheme } from "../context/ThemeContext";


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
                  location.pathname === "/" ? "nav-link active" : "nav-link"
                }
              >
                Reports
              </Link>
              <Link
                to="/dashboard"
                className={
                  location.pathname === "/dashboard"
                    ? "nav-link active"
                    : "nav-link"
                }
              >
                Dashboard
              </Link>
              {currentUser.role === "researcher" && (
                <Link
                  to="/reports/new"
                  className={
                    location.pathname === "/reports/new"
                      ? "nav-link nav-cta active"
                      : "nav-link nav-cta"
                  }
                >
                  + Submit Report
                </Link>
              )}
              {currentUser.role === "admin" && (
                <Link
                  to="/admin/users"
                  className={
                    location.pathname === "/admin/users"
                      ? "nav-link active"
                      : "nav-link"
                  }
                >
                  Admin Users
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
              <Link to="/profile" className="nav-link">
                {currentUser.name}
              </Link>
              <RoleBadge
                role={currentUser.role}
                isBanned={currentUser.is_banned}
              />
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={handleLogout}
              >
                Logout
              </button>
            </>
          ) : (
            <div className="navbar-links">
              <Link to="/login" className="nav-link">
                Login
              </Link>
              <Link to="/register" className="nav-link nav-cta">
                Register
              </Link>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
