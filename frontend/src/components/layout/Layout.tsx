import { Outlet } from "react-router-dom";
import Navbar from "./Navbar";

export default function Layout() {
  return (
    <div className="flex min-h-full flex-col">
      <Navbar />
      <main className="flex-1">
        <Outlet />
      </main>
      <footer className="border-t py-4 text-center text-xs text-slate-400 dark:text-slate-600">
        RareDx AI — Research use only. Not a clinical diagnostic device.
      </footer>
    </div>
  );
}
