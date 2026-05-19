import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { ExternalLink, Heart, Mail } from "lucide-react";

import Logo from "../brand/Logo";

/** Multi-column footer that closes the landing page. */
export default function LandingFooter() {
  const { t } = useTranslation();
  const year = new Date().getFullYear();

  const cols: { title: string; items: { label: string; href: string; external?: boolean }[] }[] = [
    {
      title: t("footer.product"),
      items: [
        { label: t("landing.navFeatures"), href: "#features" },
        { label: t("landing.navHow"),      href: "#how"      },
        { label: t("landing.navPrivacy"),  href: "#privacy"  },
        { label: t("landing.navAbout"),    href: "/about"    },
      ],
    },
    {
      title: t("footer.modules"),
      items: [
        { label: t("landing.platform1Title"), href: "#platforms" },
        { label: t("landing.platform2Title"), href: "#platforms" },
        { label: t("landing.platform3Title"), href: "#platforms" },
        { label: t("landing.platform4Title"), href: "#platforms" },
      ],
    },
    {
      title: t("footer.account"),
      items: [
        { label: t("auth.login"),    href: "/login"    },
        { label: t("auth.register"), href: "/register" },
        { label: t("auth.forgotLink"), href: "/forgot-password" },
      ],
    },
    {
      title: t("footer.contact"),
      items: [
        { label: "github.com/Diogozalao", href: "https://github.com/Diogozalao", external: true },
        { label: "diogolopesdinis@gmail.com", href: "mailto:diogolopesdinis@gmail.com", external: true },
      ],
    },
  ];

  return (
    <footer className="border-t border-stone-200 bg-stone-50/60 px-4 pt-16 pb-10 dark:border-stone-800 dark:bg-stone-950/60 sm:px-6 lg:px-10">
      <div className="mx-auto max-w-7xl">
        <div className="grid gap-10 lg:grid-cols-[1.5fr_3fr]">
          {/* Brand block */}
          <div>
            <Logo size={32} />
            <p className="mt-4 max-w-sm text-sm leading-relaxed text-stone-600 dark:text-stone-400">
              {t("footer.tagline")}
            </p>
            <div className="mt-5 flex items-center gap-2">
              <a
                href="https://github.com/Diogozalao"
                target="_blank" rel="noreferrer"
                aria-label="GitHub"
                className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-stone-200 bg-white text-stone-600 transition hover:border-stone-300 hover:text-stone-900 dark:border-stone-800 dark:bg-stone-900 dark:text-stone-300 dark:hover:border-stone-700 dark:hover:text-stone-100"
              >
                <ExternalLink className="h-4 w-4" />
              </a>
              <a
                href="mailto:diogolopesdinis@gmail.com"
                aria-label="Email"
                className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-stone-200 bg-white text-stone-600 transition hover:border-stone-300 hover:text-stone-900 dark:border-stone-800 dark:bg-stone-900 dark:text-stone-300 dark:hover:border-stone-700 dark:hover:text-stone-100"
              >
                <Mail className="h-4 w-4" />
              </a>
            </div>
          </div>

          {/* Link columns */}
          <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
            {cols.map((c) => (
              <div key={c.title}>
                <p className="text-[11px] font-semibold uppercase tracking-wider text-stone-500 dark:text-stone-500">
                  {c.title}
                </p>
                <ul className="mt-3 space-y-2 text-sm">
                  {c.items.map((it) => (
                    <li key={it.label}>
                      {it.external ? (
                        <a
                          href={it.href}
                          target="_blank" rel="noreferrer"
                          className="text-stone-700 transition hover:text-brand-600 dark:text-stone-300 dark:hover:text-brand-400"
                        >
                          {it.label}
                        </a>
                      ) : it.href.startsWith("#") ? (
                        <a
                          href={it.href}
                          className="text-stone-700 transition hover:text-brand-600 dark:text-stone-300 dark:hover:text-brand-400"
                        >
                          {it.label}
                        </a>
                      ) : (
                        <Link
                          to={it.href}
                          className="text-stone-700 transition hover:text-brand-600 dark:text-stone-300 dark:hover:text-brand-400"
                        >
                          {it.label}
                        </Link>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>

        <div className="mt-12 flex flex-wrap items-center justify-between gap-3 border-t border-stone-200 pt-6 text-xs text-stone-500 dark:border-stone-800 dark:text-stone-500">
          <p>© {year} Living Memory · {t("footer.builtBy")}</p>
          <p className="inline-flex items-center gap-1.5">
            {t("footer.madeWith")} <Heart className="h-3 w-3 text-rose-500" /> {t("footer.inPortugal")}
          </p>
        </div>
      </div>
    </footer>
  );
}
