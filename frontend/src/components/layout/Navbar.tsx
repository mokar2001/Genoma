import { Link, useLocation, useNavigate } from "react-router-dom";
import { Dna, Moon, Sun, FlaskConical, LogOut, UserCircle } from "lucide-react";
import { useThemeStore } from "@/store/themeStore";
import { useAuthStore } from "@/store/authStore";
import { cn } from "@/lib/utils";

export default function Navbar() {
  const { dark, toggle } = useThemeStore();
  const { pathname } = useLocation();
  const { token, user, logout } = useAuthStore();
  const navigate = useNavigate();

  const NAV = [
    { to: "/", label: "Home" },
    ...(token
      ? [
          { to: "/diagnose", label: "New Diagnosis" },
          { to: "/cases", label: "Cases" },
          { to: "/pipelines", label: "Pipelines" },
        ]
      : []),
  ];

  const handleLogout = () => {
    logout();
    navigate("/");
  };

  return (
    <header className="sticky top-0 z-50 border-b bg-white/80 backdrop-blur-md dark:bg-slate-900/80">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-3">
        {/* Logo */}
        <Link
          to="/"
          className="flex items-center gap-2 font-bold text-indigo-600 dark:text-indigo-400"
        >
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 shadow-md">
            <Dna className="h-5 w-5 text-white" />
          </div>
          <span className="text-lg tracking-tight">RareDx</span>
          <span className="rounded-full bg-indigo-100 px-2 py-0.5 text-xs font-medium text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300">
            AI
          </span>
        </Link>

        {/* Nav */}
        <nav className="flex items-center gap-1">
          {NAV.map(({ to, label }) => (
            <Link
              key={to}
              to={to}
              className={cn(
                "rounded-lg px-3 py-1.5 text-sm font-medium transition-colors",
                pathname === to
                  ? "bg-indigo-50 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300"
                  : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
              )}
            >
              {label}
            </Link>
          ))}

          <a
            href="http://localhost:8000/api/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="ml-1 flex items-center gap-1 rounded-lg px-3 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
          >
            <FlaskConical className="h-4 w-4" />
            API
          </a>

          <button
            onClick={toggle}
            className="ml-2 rounded-lg p-2 text-slate-500 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800"
            aria-label="Toggle dark mode"
          >
            {dark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </button>

          {token && user ? (
            <div className="ml-2 flex items-center gap-2">
              <div className="flex items-center gap-1.5 rounded-lg border border-slate-200 px-2.5 py-1.5 text-xs font-medium text-slate-600 dark:border-slate-700 dark:text-slate-300">
                <UserCircle className="h-3.5 w-3.5" />
                {user.full_name.split(" ")[0]}
              </div>
              <button
                onClick={handleLogout}
                className="rounded-lg p-2 text-slate-400 hover:bg-red-50 hover:text-red-500 dark:hover:bg-red-900/20"
                title="Sign out"
              >
                <LogOut className="h-4 w-4" />
              </button>
            </div>
          ) : (
            <Link
              to="/auth"
              className="ml-2 gradient-brand rounded-lg px-3 py-1.5 text-xs font-semibold text-white"
            >
              Sign In
            </Link>
          )}
        </nav>
      </div>
    </header>
  );
}
