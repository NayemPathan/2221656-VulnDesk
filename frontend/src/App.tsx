import React from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Navbar } from "./components/Navbar";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { AdminUsersPage } from "./pages/AdminUsersPage";
import { DashboardPage } from "./pages/DashboardPage";
import { LoginPage } from "./pages/LoginPage";
import { ProfilePage } from "./pages/ProfilePage";
import { RegisterPage } from "./pages/RegisterPage";
import { ReportDetailPage } from "./pages/ReportDetailPage";
import { ReportFormPage } from "./pages/ReportFormPage";
import { ReportListPage } from "./pages/ReportListPage";


const ProtectedRoute: React.FC<{ children: React.ReactElement }> = ({
  children,
}) => {
  const { currentUser, initializing } = useAuth();
  if (initializing) {
    return (
      <div className="page-container">
        <div className="card loading-state">Restoring secure session...</div>
      </div>
    );
  }
  if (!currentUser) {
    return <Navigate to="/login" replace />;
  }
  return children;
};


export const App: React.FC = () => {
  return (
    <AuthProvider>
      <BrowserRouter>
        <div className="app-shell">
          <Navbar />
          <main className="main-content">
            <Routes>
              <Route path="/login" element={<LoginPage />} />
              <Route path="/register" element={<RegisterPage />} />
              <Route
                path="/"
                element={
                  <ProtectedRoute>
                    <ReportListPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/dashboard"
                element={
                  <ProtectedRoute>
                    <DashboardPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/reports/new"
                element={
                  <ProtectedRoute>
                    <ReportFormPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/reports/:reportId"
                element={
                  <ProtectedRoute>
                    <ReportDetailPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/profile"
                element={
                  <ProtectedRoute>
                    <ProfilePage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/admin/users"
                element={
                  <ProtectedRoute>
                    <AdminUsersPage />
                  </ProtectedRoute>
                }
              />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </main>
          <footer className="app-footer">
            <span>
              VulnDesk Beta — Student ID <strong>2221656</strong> (CSE 309 &amp;
              CSE 451)
            </span>
          </footer>
        </div>
      </BrowserRouter>
    </AuthProvider>
  );
};


export default App;
