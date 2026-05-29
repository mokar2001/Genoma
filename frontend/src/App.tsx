import { Routes, Route } from "react-router-dom";
import { useEffect } from "react";
import { useThemeStore } from "@/store/themeStore";
import Layout from "@/components/layout/Layout";
import HomePage from "@/pages/HomePage";
import DiagnosticsPage from "@/pages/DiagnosticsPage";
import ResultsPage from "@/pages/ResultsPage";

export default function App() {
  const { dark } = useThemeStore();

  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
  }, [dark]);

  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<HomePage />} />
        <Route path="/diagnose" element={<DiagnosticsPage />} />
        <Route path="/results" element={<ResultsPage />} />
      </Route>
    </Routes>
  );
}
