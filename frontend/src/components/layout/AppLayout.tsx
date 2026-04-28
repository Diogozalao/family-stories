import { useState } from "react";
import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";
import Topbar from "./Topbar";
import { useTaskNotifications } from "../../lib/useTaskNotifications";

export default function AppLayout() {
  const [mobileOpen, setMobileOpen] = useState(false);
  useTaskNotifications();

  return (
    <div className="flex h-full bg-stone-50 dark:bg-stone-950">
      <Sidebar mobileOpen={mobileOpen} onClose={() => setMobileOpen(false)} />
      <div className="flex flex-1 flex-col min-w-0">
        <Topbar onOpenMobile={() => setMobileOpen(true)} />
        <main className="flex-1 overflow-y-auto">
          <div className="mx-auto max-w-7xl px-6 py-8 lg:px-10 lg:py-10 animate-fade-in">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
