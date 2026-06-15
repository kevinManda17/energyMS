import { useEffect } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { useAuthStore } from "./store/auth";
import ProtectedRoute from "./router/ProtectedRoute";
import DashboardLayout from "./layouts/DashboardLayout";

import Landing from "./pages/Landing";
import Pricing from "./pages/Pricing";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Dashboard from "./pages/Dashboard";
import Houses from "./pages/Houses";
import Devices from "./pages/Devices";
import Measurements from "./pages/Measurements";
import Forecasting from "./pages/Forecasting";
import Decisions from "./pages/Decisions";
import Alerts from "./pages/Alerts";
import Reports from "./pages/Reports";
import SettingsPage from "./pages/Settings";

export default function App() {
  const bootstrap = useAuthStore((s) => s.bootstrap);
  useEffect(() => {
    bootstrap();
  }, [bootstrap]);

  return (
    <Routes>
      {/* Public */}
      <Route path="/" element={<Landing />} />
      <Route path="/pricing" element={<Pricing />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />

      {/* Private */}
      <Route element={<ProtectedRoute />}>
        <Route element={<DashboardLayout />}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/houses" element={<Houses />} />
          <Route path="/devices" element={<Devices />} />
          <Route path="/measurements" element={<Measurements />} />
          <Route path="/forecasting" element={<Forecasting />} />
          <Route path="/decisions" element={<Decisions />} />
          <Route path="/alerts" element={<Alerts />} />
          <Route path="/reports" element={<Reports />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
