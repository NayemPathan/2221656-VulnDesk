/**
 * frontend/src/App.tsx
 * --------------------
 * Root application layout and React Router v6 route table:
 * - `/`                   -> ReportListPage (Read List + Search/Filter)
 * - `/reports/new`        -> ReportFormPage (Create Report)
 * - `/reports/:reportId`  -> ReportDetailPage (Read Single + Edit + Delete)
 */


import React from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Navbar } from "./components/Navbar";
import { DemoUserProvider } from "./context/DemoUserContext";
import { ReportDetailPage } from "./pages/ReportDetailPage";
import { ReportFormPage } from "./pages/ReportFormPage";
import { ReportListPage } from "./pages/ReportListPage";


export const App: React.FC = () => {
  return (
    <DemoUserProvider>
      <BrowserRouter>
        <div className="app-shell">
          <Navbar />
          <main className="main-content">
            <Routes>
              <Route path="/" element={<ReportListPage />} />
              <Route path="/reports/new" element={<ReportFormPage />} />
              <Route path="/reports/:reportId" element={<ReportDetailPage />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </main>
          <footer className="app-footer">
            <span>
              VulnDesk MVP — Student ID <strong>2221656</strong> (CSE 309 &amp;
              CSE 451)
            </span>
          </footer>
        </div>
      </BrowserRouter>
    </DemoUserProvider>
  );
};


export default App;
