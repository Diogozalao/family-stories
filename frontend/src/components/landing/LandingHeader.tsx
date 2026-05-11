import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Sparkles } from "lucide-react";
import Logo from "../brand/Logo";
import { cn } from "../../lib/utils";

/**
 * Sticky landing header — visible on the public ``/login`` and
 * ``/register`` routes. Fades from transparent to a frosted bar once
 * the user starts scrolling so the hero stays visually clean.
 */
export default function LandingHeader() {
  const { t } = useTranslation();
  const [scrolled, setScrolled] = useState(false);

  const LINKS: { label: string; href: string }[] = [
    { label: t("landing.navAbout"),    href: "/about"    },
    { label: t("landing.navFeatures"), href: "#features" },
    { label: t("landing.navHow"),      href: "#how"      },
    { label: t("landing.navPrivacy"),  href: "#privacy"  },
  ];

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className={cn(
        "fixed inset-x-0 top-0 z-30 transition-all duration-300",
        scrolled
          ? "border-b border-stone-200/80 bg-stone-50/85 backdrop-blur-md shadow-soft dark:border-stone-800/80 dark:bg-stone-950/80"
          : "border-b border-transparent bg-transparent",
      )}
    >
      <div className="mx-auto flex h-16 max-w-6xl items-center gap-4 px-4 sm:px-6">
        <a href="#top" className="flex items-center gap-2 transition hover:opacity-80">
          <Logo size={28} />
        </a>

        <nav className="ml-6 hidden items-center gap-1 md:flex">
          {LINKS.map((l) => {
            const cls =
              "rounded-lg px-3 py-1.5 text-sm font-medium text-stone-600 transition hover:bg-stone-100 hover:text-stone-900 dark:text-stone-400 dark:hover:bg-stone-900 dark:hover:text-stone-100";
            // Hash anchors stay on the landing page and use plain <a> for
            // the smooth-scroll behaviour; route paths go through <Link>
            // so the SPA doesn't full-reload.
            return l.href.startsWith("#") ? (
              <a key={l.href} href={l.href} className={cls}>{l.label}</a>
            ) : (
              <Link key={l.href} to={l.href} className={cls}>{l.label}</Link>
            );
          })}
        </nav>

        <div className="ml-auto flex items-center gap-2">
          <Link
            to="/login"
            className="hidden rounded-lg px-3 py-1.5 text-sm font-medium text-stone-700 transition hover:bg-stone-100 dark:text-stone-300 dark:hover:bg-stone-900 sm:block"
          >
            {t("landing.signIn")}
          </Link>
          <Link to="/register" className="btn btn-accent !py-1.5 !px-3 text-sm">
            <Sparkles className="h-4 w-4" />
            <span>{t("landing.getStarted")}</span>
          </Link>
        </div>
      </div>
    </header>
  );
}
