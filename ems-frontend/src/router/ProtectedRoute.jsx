import { Navigate, Outlet } from "react-router-dom";
import { useAuthStore } from "../store/auth";
import { Loading } from "../components/ui";

export default function ProtectedRoute() {
  const { isAuthenticated, loading } = useAuthStore();
  if (loading) return <Loading />;
  return isAuthenticated ? <Outlet /> : <Navigate to="/login" replace />;
}
