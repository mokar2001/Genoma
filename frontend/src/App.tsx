import { Routes, Route, Navigate, useLocation } from "react-router-dom";
import { useEffect } from "react";
import { useThemeStore } from "@/store/themeStore";
import { useAuthStore } from "@/store/authStore";
import Layout from "@/components/layout/Layout";
import HomePage from "@/pages/HomePage";
import DiagnosticsPage from "@/pages/DiagnosticsPage";
import ResultsPage from "@/pages/ResultsPage";
import CasesPage from "@/pages/CasesPage";
import AuthPage from "@/pages/AuthPage";

function RequireAuth({ children }: { children: React.ReactNode }) {
  const { token } = useAuthStore();
  const location = useLocation();
  if (!token) {
    return <Navigate to="/auth" state={{ from: location }} replace />;
  }
  return <>{children}</>;
}

export default function App() {
  const { dark } = useThemeStore();

  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
  }, [dark]);

  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<HomePage />} />
        <Route path="/auth" element={<AuthPage />} />
        <Route
          path="/diagnose"
          element={
            <RequireAuth>
              <DiagnosticsPage />
            </RequireAuth>
          }
        />
        <Route
          path="/results"
          element={
            <RequireAuth>
              <ResultsPage />
            </RequireAuth>
          }
        />
        <Route
          path="/cases"
          element={
            <RequireAuth>
              <CasesPage />
            </RequireAuth>
          }
        />
      </Route>
    </Routes>
  );
}
