import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Languages, LogIn, Menu, Sparkles, X } from "lucide-react";

import { setLanguage } from "../../i18n";
import Logo from "../brand/Logo";
import { cn } from "../../lib/utils";

/**
 * Cloudflare-inspired top nav for the public-facing pages.
 *
 * Layout: logo + brandname (left), category links (center on ≥md),
 * language toggle + Sign in + Get started CTAs (right). Below ``md``
 * the nav collapses into a hamburger sheet so the mobile hero stays
 * uncluttered.
 */
export default function LandingHeader() {
  const { t, i18n } = useTranslation();
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen]         = useState(false);

  // Section links point at the landing page (/login) + hash, so they scroll
  // to the right section even when the visitor is on /about (where those
  // sections don't exist). LoginPage handles the smooth-scroll-to-hash.
  const links: { label: string; to: string }[] = [
    { label: t("landing.navAbout"),     to: "/about"          },
    { label: t("landing.navDemo"),      to: "/login#demo"     },
    { label: t("landing.navPlatforms"), to: "/login#platforms" },
    { label: t("landing.navHow"),       to: "/login#how"      },
    { label: t("landing.navPrivacy"),   to: "/login#privacy"  },
  ];

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const toggleLang = () => setLanguage(i18n.language === "pt" ? "en" : "pt");

  return (
    <header
      className={cn(
        "fixed inset-x-0 top-0 z-40 transition-all duration-300",
        scrolled
          ? "border-b border-stone-200/80 bg-stone-50/90 backdrop-blur-md shadow-soft dark:border-stone-800/80 dark:bg-stone-950/90"
          : "border-b border-transparent bg-transparent",
      )}
    >
      <div className="mx-auto flex h-16 max-w-7xl items-center gap-3 px-4 sm:px-6 lg:px-10">
        <Link to="/" className="flex items-center gap-2 transition hover:opacity-80">
          <Logo size={38} />
        </Link>

        <nav className="ml-8 hidden items-center gap-0.5 md:flex">
          {links.map((l) => (
            <Link
              key={l.to}
              to={l.to}
              className="rounded-lg px-3 py-1.5 text-sm font-medium text-stone-700 transition hover:bg-stone-100 hover:text-stone-900 dark:text-stone-300 dark:hover:bg-stone-900 dark:hover:text-stone-100"
            >
              {l.label}
            </Link>
          ))}
        </nav>

        <div className="ml-auto flex items-center gap-2">
          {/* Lang toggle */}
          <button
            onClick={toggleLang}
            className="hidden items-center gap-1 rounded-lg border border-stone-200 bg-white px-2.5 py-1.5 text-[11px] font-semibold uppercase tracking-wider text-stone-600 transition hover:border-stone-300 hover:text-stone-900 dark:border-stone-800 dark:bg-stone-900 dark:text-stone-300 dark:hover:border-stone-700 dark:hover:text-stone-100 sm:inline-flex"
            aria-label={t("common.language")}
          >
            <Languages className="h-3.5 w-3.5" />
            {i18n.language === "pt" ? "PT" : "EN"}
          </button>

          <Link
            to="/login"
            className="hidden items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium text-stone-700 transition hover:bg-stone-100 dark:text-stone-300 dark:hover:bg-stone-900 sm:inline-flex"
          >
            <LogIn className="h-4 w-4" />
            {t("landing.signIn")}
          </Link>

          <Link
            to="/register"
            className="btn btn-accent !px-3 !py-1.5 text-sm"
          >
            <Sparkles className="h-4 w-4" />
            <span>{t("landing.getStarted")}</span>
          </Link>

          <button
            onClick={() => setOpen((v) => !v)}
            className="rounded-lg p-2 text-stone-600 hover:bg-stone-100 dark:text-stone-300 dark:hover:bg-stone-900 md:hidden"
            aria-label="Toggle menu"
          >
            {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
      </div>

      {/* Mobile sheet */}
      {open && (
        <div className="border-t border-stone-200 bg-stone-50/95 backdrop-blur dark:border-stone-800 dark:bg-stone-950/95 md:hidden">
          <div className="mx-auto max-w-7xl px-4 py-3 sm:px-6">
            <nav className="flex flex-col">
              {links.map((l) => (
                <Link
                  key={l.to}
                  to={l.to}
                  className="rounded-lg px-3 py-2 text-sm font-medium text-stone-700 hover:bg-stone-100 dark:text-stone-300 dark:hover:bg-stone-900"
                  onClick={() => setOpen(false)}
                >
                  {l.label}
                </Link>
              ))}
              <div className="my-2 h-px bg-stone-200 dark:bg-stone-800" />
              <button
                onClick={() => { toggleLang(); setOpen(false); }}
                className="rounded-lg px-3 py-2 text-left text-sm font-medium text-stone-700 hover:bg-stone-100 dark:text-stone-300 dark:hover:bg-stone-900"
              >
                {t("common.language")}: {i18n.language === "pt" ? "PT" : "EN"}
              </button>
              <Link to="/login" onClick={() => setOpen(false)} className="rounded-lg px-3 py-2 text-sm font-medium text-stone-700 hover:bg-stone-100 dark:text-stone-300 dark:hover:bg-stone-900">
                {t("landing.signIn")}
              </Link>
            </nav>
          </div>
        </div>
      )}
    </header>
  );
}
