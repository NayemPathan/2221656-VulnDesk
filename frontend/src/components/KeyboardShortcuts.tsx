import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";


export const KeyboardShortcuts: React.FC = () => {
  const { currentUser } = useAuth();
  const { toggleTheme } = useTheme();
  const navigate = useNavigate();
  const [openHelp, setOpenHelp] = useState(false);


  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      const isTyping =
        target?.tagName === "INPUT" ||
        target?.tagName === "TEXTAREA" ||
        target?.tagName === "SELECT" ||
        target?.isContentEditable;


      if (e.key === "Escape") {
        if (openHelp) {
          setOpenHelp(false);
        } else if (isTyping) {
          target?.blur();
        }
        return;
      }


      // Alt shortcuts work globally
      if (e.altKey && !e.ctrlKey && !e.metaKey) {
        const key = e.key.toLowerCase();
        if (key === "t") {
          e.preventDefault();
          toggleTheme();
        } else if (key === "d" && currentUser) {
          e.preventDefault();
          navigate("/dashboard");
        } else if (key === "r" && currentUser) {
          e.preventDefault();
          navigate("/");
        } else if (key === "n" && currentUser?.role === "researcher") {
          e.preventDefault();
          navigate("/reports/new");
        }
        return;
      }


      if (isTyping) return;


      if (e.key === "/") {
        e.preventDefault();
        const searchBox = document.getElementById("filter-keyword");
        if (searchBox) {
          searchBox.focus();
        } else if (currentUser) {
          navigate("/");
        }
      } else if (e.key === "?") {
        e.preventDefault();
        setOpenHelp((prev) => !prev);
      }
    };


    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [currentUser, navigate, toggleTheme, openHelp]);


  return (
    <>
      <button
        type="button"
        className="btn btn-secondary btn-sm shortcuts-trigger"
        onClick={() => setOpenHelp(true)}
        title="View Keyboard Shortcuts (?)"
      >
        ⌨️ Shortcuts (?)
      </button>


      {openHelp && (
        <div
          className="modal-backdrop"
          role="dialog"
          aria-modal="true"
          onClick={(e) => {
            if (e.target === e.currentTarget) setOpenHelp(false);
          }}
        >
          <div className="card modal-card">
            <div className="section-header-inline">
              <h3 className="section-title">Keyboard Shortcuts</h3>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => setOpenHelp(false)}
              >
                Close (Esc)
              </button>
            </div>
            <div className="shortcuts-grid mt-3">
              <div className="stat-row">
                <span>Focus Report Search</span>
                <kbd className="kbd-key">/</kbd>
              </div>
              <div className="stat-row">
                <span>Toggle Light / Dark Mode</span>
                <kbd className="kbd-key">Alt + T</kbd>
              </div>
              <div className="stat-row">
                <span>Go to Reports Queue</span>
                <kbd className="kbd-key">Alt + R</kbd>
              </div>
              <div className="stat-row">
                <span>Go to Dashboard</span>
                <kbd className="kbd-key">Alt + D</kbd>
              </div>
              <div className="stat-row">
                <span>New Report (Researcher)</span>
                <kbd className="kbd-key">Alt + N</kbd>
              </div>
              <div className="stat-row">
                <span>Close Modals / Blur Input</span>
                <kbd className="kbd-key">Esc</kbd>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
