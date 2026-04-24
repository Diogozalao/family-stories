import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { LogOut, Menu, Moon, Sun, Monitor } from "lucide-react";
import { toast } from "sonner";
import { useAuthStore } from "../../store/auth";
import { useThemeStore } from "../../store/theme";
import { cn, initials } from "../../lib/utils";

export default function Topbar({ onOpenMobile }: { onOpenMobile: () => void }) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const user    = useAuthStore((s) => s.user);
  const logout  = useAuthStore((s) => s.logout);
  const mode    = useThemeStore((s) => s.mode);
  const setMode = useThemeStore((s) => s.setMode);

  const cycleTheme = () => {
    const next = mode === "light" ? "dark" : mode === "dark" ? "system" : "light";
    setMode(next);
  };

  const ThemeIcon = mode === "light" ? Sun : mode === "dark" ? Moon : Monitor;

  const handleLogout = () => {
    logout();
    toast.success(t("auth.loggedOut"));
    navigate("/login");
  };

  return (
    <header className="sticky top-0 z-20 flex h-16 items-center gap-3 border-b border-stone-200 bg-stone-50/80 px-4 backdrop-blur-md dark:border-stone-800 dark:bg-stone-950/80 lg:px-10">
      <button
        className="rounded-lg p-2 text-stone-600 hover:bg-stone-100 dark:text-stone-300 dark:hover:bg-stone-900 lg:hidden"
        onClick={onOpenMobile}
        aria-label="Open menu"
      >
        <Menu className="h-5 w-5" />
      </button>

      <div className="flex-1" />

      <button
        onClick={cycleTheme}
        className={cn(
          "relative rounded-lg border border-stone-200 bg-white p-2 text-stone-600 shadow-soft transition",
          "hover:text-stone-900 hover:border-stone-300",
          "dark:border-stone-800 dark:bg-stone-900 dark:text-stone-300 dark:hover:text-stone-100 dark:hover:border-stone-700",
        )}
        title={mode}
        aria-label="Toggle theme"
      >
        <ThemeIcon className="h-[18px] w-[18px]" />
      </button>

      <div className="flex items-center gap-3 rounded-xl border border-stone-200 bg-white px-3 py-1.5 shadow-soft dark:border-stone-800 dark:bg-stone-900">
        <div className="flex h-7 w-7 items-center justify-center rounded-full bg-gradient-to-br from-brand-400 to-brand-600 text-xs font-semibold text-white">
          {initials(user?.username ?? "?")}
        </div>
        <div className="hidden sm:block">
          <p className="text-sm font-medium leading-tight">{user?.username}</p>
          {user?.is_owner && (
            <p className="text-[10px] uppercase tracking-wider text-stone-500 dark:text-stone-400">
              owner
            </p>
          )}
        </div>
        <button
          onClick={handleLogout}
          className="rounded-lg p-1.5 text-stone-500 hover:bg-stone-100 hover:text-stone-900 dark:hover:bg-stone-800 dark:hover:text-stone-100"
          aria-label={t("common.signOut")}
          title={t("common.signOut")}
        >
          <LogOut className="h-4 w-4" />
        </button>
      </div>
    </header>
  );
}
