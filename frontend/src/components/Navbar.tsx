/**
 * frontend/src/components/Navbar.tsx
 * ----------------------------------
 * Top navigation bar featuring:
 * 1. Brand identity ("VulnDesk") and quick navigation links ("Reports Queue",
 *    "+ Submit Report" when acting as a Researcher).
 * 2. Live Demo Persona Switcher dropdown so your course instructor can switch
 *    between Alice, Bob, Mallory (Banned), Charlie (Analyst), and Nadia (Admin)
 *    in one click and immediately watch ownership isolation and UI permissions update.
 */


import React from "react";
import { Link, useLocation } from "react-router-dom";
import { useDemoUser } from "../context/DemoUserContext";
import { RoleBadge } from "./Badges";


export const Navbar: React.FC = () => {
  const { users, currentUser, selectUserByEmail } = useDemoUser();
  const location = useLocation();


  return (
    <header className="navbar">
      <div className="navbar-container">
        <div className="navbar-left">
          <Link to="/" className="navbar-brand">
            <span className="brand-shield">🛡️</span>
            <div>
              <span className="brand-title">VulnDesk</span>
              <span className="brand-subtitle">Vulnerability Triage & RBAC</span>
            </div>
          </Link>


          <nav className="navbar-links">
            <Link
              to="/"
              className={
                location.pathname === "/" ? "nav-link active" : "nav-link"
              }
            >
              Reports Queue
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
          </nav>
        </div>


        <div className="navbar-right">
          <div className="persona-switcher">
            <label htmlFor="demo-persona-select" className="persona-label">
              Active Demo Persona (`X-Demo-User`):
            </label>
            <div className="persona-controls">
              <select
                id="demo-persona-select"
                className="persona-select"
                value={currentUser.email}
                onChange={(e) => selectUserByEmail(e.target.value)}
              >
                {users.map((u) => (
                  <option key={u.id} value={u.email}>
                    {u.name} — {u.email}
                    {u.is_banned ? " [BANNED]" : ""}
                  </option>
                ))}
              </select>
              <RoleBadge
                role={currentUser.role}
                isBanned={currentUser.is_banned}
              />
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};
