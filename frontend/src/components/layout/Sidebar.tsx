import { NavLink } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  BookOpen, Clapperboard, Clock, FolderKanban, Home, Images,
  Settings, Sparkles, Users, X,
} from "lucide-react";
import Logo from "../brand/Logo";
import { cn } from "../../lib/utils";
import type { ReactNode } from "react";

interface Item {
  to: string;
  icon: ReactNode;
  label: string;
  accent?: boolean;
}

export default function Sidebar({
  mobileOpen,
  onClose,
}: {
  mobileOpen: boolean;
  onClose: () => void;
}) {
  const { t } = useTranslation();

  const items: Item[] = [
    { to: "/",         icon: <Home         className="h-[18px] w-[18px]" />, label: t("nav.dashboard") },
    { to: "/library",  icon: <Images       className="h-[18px] w-[18px]" />, label: t("nav.library") },
    { to: "/family",   icon: <Users        className="h-[18px] w-[18px]" />, label: t("nav.family") },
    { to: "/timeline", icon: <Clock        className="h-[18px] w-[18px]" />, label: t("nav.timeline") },
    { to: "/projects", icon: <FolderKanban className="h-[18px] w-[18px]" />, label: t("nav.projects") },
    { to: "/generate", icon: <Sparkles     className="h-[18px] w-[18px]" />, label: t("nav.generate"), accent: true },
    { to: "/stories",  icon: <BookOpen     className="h-[18px] w-[18px]" />, label: t("nav.stories") },
    { to: "/videos",   icon: <Clapperboard className="h-[18px] w-[18px]" />, label: t("nav.videos") },
    // "Tarefas" intentionally hidden from the nav: generation runs synchronously,
    // so the task queue is always empty for end users. Backend infra is kept
    // (route still reachable at /tasks) for the report's background-jobs section.
    { to: "/settings", icon: <Settings     className="h-[18px] w-[18px]" />, label: t("nav.settings") },
  ];

  const content = (
    <div className="flex h-full flex-col gap-1 p-4">
      <div className="px-2 pt-2 pb-6">
        <Logo />
      </div>

      <nav className="flex flex-col gap-0.5">
        {items.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/"}
            onClick={onClose}
            className={({ isActive }) =>
              cn(
                "group flex items-center gap-3 rounded-xl px-3 py-2 text-sm font-medium transition",
                isActive
                  ? "bg-stone-900 text-white dark:bg-stone-100 dark:text-stone-900"
                  : "text-stone-600 hover:bg-stone-100 hover:text-stone-900 dark:text-stone-400 dark:hover:bg-stone-900 dark:hover:text-stone-100",
                item.accent && "relative",
              )
            }
          >
            {item.icon}
            <span>{item.label}</span>
            {item.accent && (
              <span className="ml-auto h-1.5 w-1.5 rounded-full bg-brand-400" />
            )}
          </NavLink>
        ))}
      </nav>

      <div className="mt-auto pt-6">
        <div className="rounded-xl border border-stone-200 bg-white p-4 dark:border-stone-800 dark:bg-stone-900">
          <p className="text-xs leading-relaxed text-stone-600 dark:text-stone-400">
            {t("app.tagline")}
          </p>
        </div>
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop */}
      <aside className="hidden lg:flex lg:w-64 lg:shrink-0 lg:border-r lg:border-stone-200 lg:bg-white dark:lg:border-stone-800 dark:lg:bg-stone-900">
        <div className="flex w-full flex-col">{content}</div>
      </aside>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div className="fixed inset-0 z-40 flex lg:hidden">
          <div
            className="absolute inset-0 bg-stone-900/40 backdrop-blur-sm animate-fade-in"
            onClick={onClose}
          />
          <aside className="relative w-72 max-w-[80vw] border-r border-stone-200 bg-white dark:border-stone-800 dark:bg-stone-900 animate-slide-up">
            <button
              className="absolute right-3 top-3 rounded-lg p-1.5 text-stone-500 hover:bg-stone-100 dark:hover:bg-stone-800"
              onClick={onClose}
              aria-label="Close"
            >
              <X className="h-5 w-5" />
            </button>
            {content}
          </aside>
        </div>
      )}
    </>
  );
}
