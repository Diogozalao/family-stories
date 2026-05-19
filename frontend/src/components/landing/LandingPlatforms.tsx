import { useTranslation } from "react-i18next";
import {
  ArrowRight, Camera, Film, Network, Sparkles, type LucideIcon,
} from "lucide-react";

import { cn } from "../../lib/utils";

interface Platform {
  tag:    string;
  icon:   LucideIcon;
  title:  string;
  body:   string;
  bullet: string[];
  tone:   string;
}

/**
 * Cloudflare's homepage has a "platforms" grid where the user can pick
 * the entry point they care about. We mirror that with the four M-modules
 * — each card is the natural opening into a different part of the app.
 */
export function LandingPlatforms() {
  const { t } = useTranslation();

  const platforms: Platform[] = [
    {
      tag:   "M1",
      icon:  Camera,
      title: t("landing.platform1Title"),
      body:  t("landing.platform1Body"),
      bullet:[t("landing.platform1B1"), t("landing.platform1B2"), t("landing.platform1B3")],
      tone:  "from-amber-200/60 to-amber-100/30 dark:from-amber-900/30 dark:to-amber-950/10",
    },
    {
      tag:   "M2",
      icon:  Network,
      title: t("landing.platform2Title"),
      body:  t("landing.platform2Body"),
      bullet:[t("landing.platform2B1"), t("landing.platform2B2"), t("landing.platform2B3")],
      tone:  "from-sky-200/60 to-sky-100/30 dark:from-sky-900/30 dark:to-sky-950/10",
    },
    {
      tag:   "M3",
      icon:  Sparkles,
      title: t("landing.platform3Title"),
      body:  t("landing.platform3Body"),
      bullet:[t("landing.platform3B1"), t("landing.platform3B2"), t("landing.platform3B3")],
      tone:  "from-rose-200/60 to-rose-100/30 dark:from-rose-900/30 dark:to-rose-950/10",
    },
    {
      tag:   "M4",
      icon:  Film,
      title: t("landing.platform4Title"),
      body:  t("landing.platform4Body"),
      bullet:[t("landing.platform4B1"), t("landing.platform4B2"), t("landing.platform4B3")],
      tone:  "from-emerald-200/60 to-emerald-100/30 dark:from-emerald-900/30 dark:to-emerald-950/10",
    },
  ];

  return (
    <section id="platforms" className="relative border-y border-stone-200 bg-white py-20 dark:border-stone-800 dark:bg-stone-900/30 sm:py-24">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-10">
        <header className="mx-auto max-w-3xl text-center">
          <span className="inline-flex items-center rounded-full border border-stone-200 bg-stone-50 px-3 py-1 text-[11px] font-semibold uppercase tracking-wider text-stone-700 dark:border-stone-800 dark:bg-stone-900 dark:text-stone-300">
            {t("landing.platformsTag")}
          </span>
          <h2 className="mt-4 font-serif text-3xl font-semibold tracking-tight sm:text-4xl">
            {t("landing.platformsTitle")}
          </h2>
          <p className="mt-3 text-[15px] text-stone-600 dark:text-stone-400">
            {t("landing.platformsLead")}
          </p>
        </header>

        <div className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {platforms.map((p) => (
            <article
              key={p.tag}
              className="group relative overflow-hidden rounded-3xl border border-stone-200 bg-white p-6 shadow-soft transition hover:-translate-y-1 hover:shadow-lift dark:border-stone-800 dark:bg-stone-900"
            >
              <div className={cn(
                "pointer-events-none absolute -right-12 -top-12 h-32 w-32 rounded-full bg-gradient-to-br blur-2xl opacity-80 transition group-hover:opacity-100",
                p.tone,
              )} />
              <div className="relative">
                <div className="flex items-center justify-between">
                  <span className="inline-flex h-10 w-10 items-center justify-center rounded-xl bg-stone-900 text-white dark:bg-stone-100 dark:text-stone-900">
                    <p.icon className="h-5 w-5" />
                  </span>
                  <span className="font-mono text-[11px] font-semibold tracking-wider text-stone-400 dark:text-stone-500">
                    {p.tag}
                  </span>
                </div>
                <h3 className="mt-4 font-serif text-lg font-semibold leading-snug tracking-tight">
                  {p.title}
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-stone-600 dark:text-stone-400">
                  {p.body}
                </p>
                <ul className="mt-4 space-y-1.5 border-t border-stone-100 pt-4 text-xs text-stone-600 dark:border-stone-800 dark:text-stone-400">
                  {p.bullet.map((b) => (
                    <li key={b} className="flex items-start gap-1.5">
                      <ArrowRight className="mt-0.5 h-3 w-3 shrink-0 text-brand-500 dark:text-brand-400" />
                      <span>{b}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

/** Trust bar — names the tech stack so the visitor knows what's under the hood. */
export function LandingTrustBar() {
  const { t } = useTranslation();
  const items = [
    "Gemini Vision",
    "Llama 3.1 · Ollama",
    "Supabase",
    "MoviePy",
    "Tesseract OCR",
    "ChromaDB",
  ];
  return (
    <section className="relative py-10 sm:py-12">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-10">
        <p className="text-center text-[11px] font-semibold uppercase tracking-[0.18em] text-stone-500 dark:text-stone-500">
          {t("landing.poweredBy")}
        </p>
        <ul className="mt-5 flex flex-wrap items-center justify-center gap-x-8 gap-y-3 text-sm text-stone-700 dark:text-stone-300">
          {items.map((name) => (
            <li key={name} className="font-medium tracking-tight">{name}</li>
          ))}
        </ul>
      </div>
    </section>
  );
}

/** Big-number stats — the social-proof analogue of Cloudflare's "X% of the internet". */
export function LandingStats() {
  const { t } = useTranslation();
  const stats = [
    { value: "4",       suffix: "",   label: t("landing.statModules"),    accent: false },
    { value: "100%",    suffix: "",   label: t("landing.statLocal"),      accent: true  },
    { value: "PT-PT",   suffix: "",   label: t("landing.statLanguage"),   accent: false },
    { value: "0",       suffix: "€",  label: t("landing.statCost"),       accent: false },
  ];
  return (
    <section className="relative py-20 sm:py-24">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-10">
        <header className="mx-auto max-w-3xl text-center">
          <span className="inline-flex items-center rounded-full border border-stone-200 bg-stone-50 px-3 py-1 text-[11px] font-semibold uppercase tracking-wider text-stone-700 dark:border-stone-800 dark:bg-stone-900 dark:text-stone-300">
            {t("landing.statsTag")}
          </span>
          <h2 className="mt-4 font-serif text-3xl font-semibold tracking-tight sm:text-4xl">
            {t("landing.statsTitle")}
          </h2>
        </header>
        <div className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {stats.map((s) => (
            <div
              key={s.label}
              className={cn(
                "rounded-3xl border p-7 text-center transition hover:-translate-y-0.5 hover:shadow-lift",
                s.accent
                  ? "border-amber-200 bg-gradient-to-br from-amber-50 to-brand-50 shadow-soft dark:border-amber-900/40 dark:from-amber-950/30 dark:to-brand-950/30"
                  : "border-stone-200 bg-white shadow-soft dark:border-stone-800 dark:bg-stone-900",
              )}
            >
              <p className="font-serif text-5xl font-semibold tracking-tight">
                {s.value}
                <span className="text-2xl text-stone-500">{s.suffix}</span>
              </p>
              <p className="mt-2 text-xs uppercase tracking-wider text-stone-500 dark:text-stone-500">
                {s.label}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
